import ifctester.ids as ids

spec_doc = ids.Ids(
    title="PRJ01 Client Exchange Information Requirements (EIR)",
    copyright="Al-Amin BIM Governance",
    version="1.0",
    purpose="Milestone Gate 03 - Handover & Fire Compliance",
)

# Specification 1: Every IfcWall must have Pset_WallCommon.FireRating
wall_spec = ids.Specification(
    name="WALL-FIRE-01: Mandatory Wall Fire Rating",
    ifcVersion=["IFC4"],
    identifier="IDS-001",
    description="All walls must carry a valid FireRating in Pset_WallCommon.",
)
wall_spec.applicability.append(ids.Entity(name="IFCWALL"))
wall_spec.requirements.append(
    ids.Property(
        baseName="FireRating",
        propertySet="Pset_WallCommon",
        cardinality="required",
    )
)
spec_doc.specifications.append(wall_spec)

# Specification 2: Every IfcDoor must have a populated Name attribute
door_spec = ids.Specification(
    name="DOOR-ID-01: Mandatory Door Tag/Name",
    ifcVersion=["IFC4"],
    identifier="IDS-002",
    description="All doors must have a populated Name attribute for COBie schedules.",
)
door_spec.applicability.append(ids.Entity(name="IFCDOOR"))
door_spec.requirements.append(ids.Attribute(name="Name", cardinality="required"))
spec_doc.specifications.append(door_spec)

spec_doc.to_xml("client_eir_requirements.ids")
print("Generated valid IDS 1.0 XML: client_eir_requirements.ids")
