import ifcopenshell
import ifcopenshell.api

model = ifcopenshell.api.run("project.create_file", version="IFC4")
project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="PRJ01")
site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="SITE_01")
building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="BLDG_01")
storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="LVL_01")

ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

# 1. Fully Compliant Walls (Valid Name + Pset_WallCommon.FireRating)
for i, rating in [(1, "EI60"), (2, "EI90")]:
    wall = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWall", name=f"ARC_WALL_EXT0{i}")
    ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[wall])
    pset = ifcopenshell.api.run("pset.add_pset", model, product=wall, name="Pset_WallCommon")
    ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={"FireRating": rating, "IsExternal": True})

# 2. Wall with valid name but MISSING FireRating (Fails Pset QA/QC)
wall_no_fire = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWall", name="ARC_WALL_INT03")
ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[wall_no_fire])

# 3. Non-Compliant Elements (Bad name, missing name, generic proxy)
bad_wall = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWall", name="Default Generic Wall")
unnamed_door = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcDoor", name=None)
proxy_obj = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingElementProxy", name="TMP_OBJ_01")

ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[bad_wall, unnamed_door, proxy_obj])

model.write("PRJ01-ARC-ZZ-01-M3-A-0001.ifc")
print("Generated IFC4 test model with Pset_WallCommon test cases.")
