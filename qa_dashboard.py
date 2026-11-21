import marimo

__generated_with = "0.10.0"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import ifcopenshell
    import ifctester.ids as ids
    import bimpolars as bpl
    return bpl, ids, ifcopenshell, mo, pl


@app.cell
def _(bpl, ids, ifcopenshell, mo, pl):
    ifc_path = "PRJ01-ARC-ZZ-01-M3-A-0001.ifc"
    ids_path = "client_eir_requirements.ids"

    bdf = bpl.read_ifc(ifc_path)
    df = bdf.frame
    id_col = "GlobalId" if "GlobalId" in df.columns else "id"
    name_col = "Name" if "Name" in df.columns else "name"

    flat_cols = [
        c for c, dt in df.schema.items()
        if c not in ("mesh", "geometry") and not isinstance(dt, (pl.List, pl.Struct, pl.Array, pl.Object))
    ]
    base_df = df.select(flat_cols).with_columns(pl.col(id_col).cast(pl.Utf8))

    model = ifcopenshell.open(ifc_path)
    ids_doc = ids.open(ids_path)
    ids_doc.validate(model)

    failures = []
    for spec in ids_doc.specifications:
        for ent in spec.failed_entities:
            guid = getattr(ent, "GlobalId", None)
            if guid:
                failures.append({id_col: guid, "failed_rule": spec.name})

    fail_df = (
        pl.DataFrame(failures).group_by(id_col).agg(pl.col("failed_rule").str.join(" | ").alias("ids_status"))
        if failures else pl.DataFrame(schema={id_col: pl.Utf8, "ids_status": pl.Utf8})
    )

    audit_df = base_df.join(fail_df, on=id_col, how="left").with_columns([
        pl.col("ids_status").fill_null("PASS"),
        (pl.col("class") == "IfcBuildingElementProxy").alias("is_proxy"),
    ])

    mo.md(f"## ISO 19650 & IDS Interactive QA/QC Gatekeeper (`{ifc_path}`)")
    return audit_df, id_col, name_col


@app.cell
def _(audit_df, mo):
    status_filter = mo.ui.dropdown(
        options=["All Elements", "Failed IDS Only", "Unclassified Proxies Only", "Passed Only"],
        value="Failed IDS Only",
        label="QA/QC Filter:",
    )
    class_options = ["All Classes"] + sorted(audit_df["class"].cast(str).unique().to_list())
    class_filter = mo.ui.dropdown(options=class_options, value="All Classes", label="IFC Class:")
    mo.hstack([status_filter, class_filter])
    return class_filter, status_filter


@app.cell
def _(audit_df, class_filter, mo, pl, status_filter):
    filtered = audit_df
    if status_filter.value == "Failed IDS Only":
        filtered = filtered.filter(pl.col("ids_status") != "PASS")
    elif status_filter.value == "Unclassified Proxies Only":
        filtered = filtered.filter(pl.col("is_proxy"))
    elif status_filter.value == "Passed Only":
        filtered = filtered.filter((pl.col("ids_status") == "PASS") & (~pl.col("is_proxy")))

    if class_filter.value != "All Classes":
        filtered = filtered.filter(pl.col("class").cast(str) == class_filter.value)

    mo.vstack([
        mo.md(f"**Showing {filtered.height} of {audit_df.height} elements**"),
        mo.ui.table(filtered),
    ])
    return


if __name__ == "__main__":
    app.run()
