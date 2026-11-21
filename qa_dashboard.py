import marimo

__generated_with = "0.10.0"
app = marimo.App(width="full")


@app.cell
def _():
    import io
    import uuid
    import zipfile
    from datetime import datetime, timezone
    from xml.sax.saxutils import escape
    import marimo as mo
    import polars as pl
    import plotly.express as px
    import ifcopenshell
    import ifcopenshell.util.placement
    import ifctester.ids as ids
    import bimpolars as bpl
    return (
        bpl,
        datetime,
        escape,
        ids,
        ifcopenshell,
        io,
        mo,
        pl,
        px,
        timezone,
        uuid,
        zipfile,
    )


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
    return audit_df, id_col, ifc_path, name_col


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
def _(
    audit_df,
    class_filter,
    datetime,
    escape,
    id_col,
    ifc_path,
    io,
    mo,
    name_col,
    pl,
    px,
    status_filter,
    timezone,
    uuid,
    zipfile,
):
    filtered = audit_df
    if status_filter.value == "Failed IDS Only":
        filtered = filtered.filter(pl.col("ids_status") != "PASS")
    elif status_filter.value == "Unclassified Proxies Only":
        filtered = filtered.filter(pl.col("is_proxy"))
    elif status_filter.value == "Passed Only":
        filtered = filtered.filter((pl.col("ids_status") == "PASS") & (~pl.col("is_proxy")))

    if class_filter.value != "All Classes":
        filtered = filtered.filter(pl.col("class").cast(str) == class_filter.value)

    # Build standard BCF 2.1 (.bcfzip) archive for all failed IDS elements in the current filtered view
    failed_subset = filtered.filter(pl.col("ids_status") != "PASS")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def build_bcf21_bytes(rows_df: pl.DataFrame) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "bcf.version",
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                "<Version VersionId=\"2.1\" xsi:noNamespaceSchemaLocation=\"version.xsd\" "
                "xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">\n"
                "  <DetailedVersion>2.1</DetailedVersion>\n"
                "</Version>\n",
            )
            for idx, row in enumerate(rows_df.to_dicts(), start=1):
                topic_guid = str(uuid.uuid4())
                vp_guid = str(uuid.uuid4())
                ifc_guid = escape(str(row[id_col]))
                ifc_cls = escape(str(row["class"]))
                el_name = escape(str(row[name_col] or "<UNNAMED>"))
                rule_txt = escape(str(row["ids_status"]))
                x_val, y_val, z_val = float(row["x_m"]), float(row["y_m"]), float(row["z_m"])

                markup = (
                    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                    "<Markup xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
                    "xsi:noNamespaceSchemaLocation=\"markup.xsd\">\n"
                    f"  <Header><File IfcProject=\"PRJ01\" isExternal=\"true\"><Filename>{escape(ifc_path)}</Filename><Date>{now_iso}</Date></File></Header>\n"
                    f"  <Topic Guid=\"{topic_guid}\" TopicType=\"Error\" TopicStatus=\"Open\">\n"
                    f"    <ReferenceLink>{ifc_guid}</ReferenceLink>\n"
                    f"    <Title>[IDS QA/QC #{idx:02d}] {ifc_cls} ({el_name}) - {rule_txt}</Title>\n"
                    f"    <Priority>High</Priority>\n"
                    f"    <Index>{idx}</Index>\n"
                    f"    <CreationDate>{now_iso}</CreationDate>\n"
                    f"    <CreationAuthor>bimpolars-qa-gatekeeper</CreationAuthor>\n"
                    f"    <Description>Failed buildingSMART IDS 1.0 rule(s): {rule_txt}. Coordinates: ({x_val}, {y_val}, {z_val})m.</Description>\n"
                    f"  </Topic>\n"
                    f"  <Viewpoints Guid=\"{vp_guid}\">\n"
                    f"    <Viewpoint>viewpoint.bcfv</Viewpoint>\n"
                    f"  </Viewpoints>\n"
                    "</Markup>\n"
                )
                viewpoint = (
                    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                    "<VisualizationInfo xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
                    "xsi:noNamespaceSchemaLocation=\"visinfo.xsd\">\n"
                    "  <Components>\n"
                    "    <Selection>\n"
                    f"      <Component IfcGuid=\"{ifc_guid}\" />\n"
                    "    </Selection>\n"
                    "    <Visibility DefaultVisibility=\"true\" />\n"
                    "  </Components>\n"
                    "  <PerspectiveCamera>\n"
                    f"    <CameraViewPoint><X>{x_val + 4.0}</X><Y>{y_val - 4.0}</Y><Z>{z_val + 3.0}</Z></CameraViewPoint>\n"
                    "    <CameraDirection><X>-0.6</X><Y>0.6</Y><Z>-0.4</Z></CameraDirection>\n"
                    "    <CameraUpVector><X>0.0</X><Y>0.0</Y><Z>1.0</Z></CameraUpVector>\n"
                    "    <FieldOfView>60.0</FieldOfView>\n"
                    "  </PerspectiveCamera>\n"
                    "</VisualizationInfo>\n"
                )
                zf.writestr(f"{topic_guid}/markup.bcf", markup)
                zf.writestr(f"{topic_guid}/viewpoint.bcfv", viewpoint)
        return buf.getvalue()

    bcf_bytes = build_bcf21_bytes(failed_subset)
    bcf_btn = mo.download(
        data=bcf_bytes,
        filename="filtered_ids_issues.bcfzip",
        mimetype="application/zip",
        label=f"Download BCF 2.1 Issues ({failed_subset.height} Failed Elements)",
        disabled=failed_subset.height == 0,
    )

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
        bcf_btn,
        mo.ui.plotly(fig),
        mo.md(f"**Filtered Audit Records ({filtered.height} of {audit_df.height} elements):**"),
        mo.ui.table(filtered),
    ])
    return


if __name__ == "__main__":
    app.run()
