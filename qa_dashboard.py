import marimo

__generated_with = "0.10.0"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import plotly.express as px
    import ifcopenshell
    import ifcopenshell.util.placement
    import ifctester.ids as ids
    import bimpolars as bpl
    return bpl, ids, ifcopenshell, mo, pl, px


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

    # Extract 3D local placement coordinates (X, Y, Z) for every IFC element
    coord_rows = []
    for idx, prod in enumerate(model.by_type("IfcProduct")):
        guid = getattr(prod, "GlobalId", None)
        if not guid:
            continue
        if getattr(prod, "ObjectPlacement", None):
            mat = ifcopenshell.util.placement.get_local_placement(prod.ObjectPlacement)
            x, y, z = float(mat[0, 3]), float(mat[1, 3]), float(mat[2, 3])
        else:
            x, y, z = float(idx * 1.5), -2.0, 0.0
        coord_rows.append({id_col: guid, "x_m": round(x, 3), "y_m": round(y, 3), "z_m": round(z, 3)})

    coords_df = (
        pl.DataFrame(coord_rows)
        if coord_rows else pl.DataFrame(schema={id_col: pl.Utf8, "x_m": pl.Float64, "y_m": pl.Float64, "z_m": pl.Float64})
    )

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

    audit_df = (
        base_df
        .join(fail_df, on=id_col, how="left")
        .join(coords_df, on=id_col, how="left")
        .with_columns([
            pl.col("ids_status").fill_null("PASS"),
            (pl.col("class") == "IfcBuildingElementProxy").alias("is_proxy"),
            pl.col("x_m").fill_null(0.0),
            pl.col("y_m").fill_null(0.0),
            pl.col("z_m").fill_null(0.0),
        ])
        .with_columns([
            pl.when(pl.col("ids_status") != "PASS")
            .then(pl.lit("FAILED IDS"))
            .when(pl.col("is_proxy"))
            .then(pl.lit("UNCLASSIFIED PROXY"))
            .otherwise(pl.lit("PASS"))
            .alias("qa_badge")
        ])
    )

    total_el = audit_df.height
    failed_el = audit_df.filter(pl.col("ids_status") != "PASS").height
    pass_pct = round(((total_el - failed_el) / total_el) * 100, 1) if total_el else 100.0

    mo.vstack([
        mo.md(f"## ISO 19650 & IDS Interactive 3D QA/QC Gatekeeper (`{ifc_path}`)"),
        mo.hstack([
            mo.stat(label="Total Audited Entities", value=str(total_el)),
            mo.stat(label="Failed IDS Items", value=str(failed_el)),
            mo.stat(label="Overall Pass Rate", value=f"{pass_pct}%"),
        ]),
    ])
    return audit_df, id_col, name_col


@app.cell
def _(audit_df, mo):
    status_filter = mo.ui.dropdown(
        options=["All Elements", "Failed IDS Only", "Unclassified Proxies Only", "Passed Only"],
        value="All Elements",
        label="QA/QC Status Filter:",
    )
    class_options = ["All Classes"] + sorted(audit_df["class"].cast(str).unique().to_list())
    class_filter = mo.ui.dropdown(options=class_options, value="All Classes", label="IFC Class:")
    mo.hstack([status_filter, class_filter])
    return class_filter, status_filter


@app.cell
def _(audit_df, class_filter, id_col, mo, name_col, pl, px, status_filter):
    filtered = audit_df
    if status_filter.value == "Failed IDS Only":
        filtered = filtered.filter(pl.col("ids_status") != "PASS")
    elif status_filter.value == "Unclassified Proxies Only":
        filtered = filtered.filter(pl.col("is_proxy"))
    elif status_filter.value == "Passed Only":
        filtered = filtered.filter((pl.col("ids_status") == "PASS") & (~pl.col("is_proxy")))

    if class_filter.value != "All Classes":
        filtered = filtered.filter(pl.col("class").cast(str) == class_filter.value)

    plot_df = filtered.with_columns([
        pl.col(name_col).cast(pl.Utf8).fill_null("<UNNAMED>").alias("display_name"),
        pl.col("class").cast(pl.Utf8).alias("ifc_class"),
    ]).to_dicts()

    fig = px.scatter_3d(
        plot_df,
        x="x_m",
        y="y_m",
        z="z_m",
        color="qa_badge",
        symbol="qa_badge",
        hover_name="display_name",
        hover_data={
            id_col: True,
            "ifc_class": True,
            "ids_status": True,
            "x_m": True,
            "y_m": True,
            "z_m": True,
        },
        color_discrete_map={
            "FAILED IDS": "#EF4444",
            "UNCLASSIFIED PROXY": "#F59E0B",
            "PASS": "#10B981",
        },
        symbol_map={
            "FAILED IDS": "diamond",
            "UNCLASSIFIED PROXY": "square",
            "PASS": "circle",
        },
        title="3D Spatial QA/QC Model View (Red = Failed IDS Requirement)",
        height=520,
    )
    fig.update_traces(marker=dict(size=9, line=dict(width=1, color="#111827")))
    fig.update_layout(
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Elevation Z (m)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, b=0, t=40),
    )

    mo.vstack([
        mo.ui.plotly(fig),
        mo.md(f"**Filtered Audit Records ({filtered.height} of {audit_df.height} elements):**"),
        mo.ui.table(filtered),
    ])
    return


if __name__ == "__main__":
    app.run()
