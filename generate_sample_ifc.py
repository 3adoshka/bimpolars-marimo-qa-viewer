import numpy as np
import ifcopenshell
import ifcopenshell.api

def place_at(model, product, x: float, y: float, z: float = 0.0):
    matrix = np.eye(4)
    matrix[0, 3], matrix[1, 3], matrix[2, 3] = x, y, z
    ifcopenshell.api.run("geometry.edit_object_placement", model, product=product, matrix=matrix)

model = ifcopenshell.api.run("project.create_file", version="IFC4")
project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="PRJ01")
site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="SITE_01")
building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="BLDG_01")
storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="LVL_01")

ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

# 1. Compliant Walls (Valid Name + Pset_WallCommon.FireRating)
for i, rating, coords in [(1, "EI60", (0.0, 0.0, 0.0)), (2, "EI90", (6.0, 0.0, 0.0))]:
    wall = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWall", name=f"ARC_WALL_EXT0{i}")
    ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[wall])
    place_at(model, wall, *coords)
    pset = ifcopenshell.api.run("pset.add_pset", model, product=wall, name="Pset_WallCommon")
    ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={"FireRating": rating, "IsExternal": True})

# 2. Non-Compliant Wall (Missing FireRating)
wall_no_fire = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWall", name="ARC_WALL_INT03")
ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[wall_no_fire])
place_at(model, wall_no_fire, 3.0, 4.0, 0.0)

# 3. Non-Compliant Wall (Bad Name + Missing FireRating), Unnamed Door & Proxy
bad_wall = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWall", name="Default Generic Wall")
unnamed_door = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcDoor", name=None)
proxy_obj = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingElementProxy", name="TMP_OBJ_01")

ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[bad_wall, unnamed_door, proxy_obj])
place_at(model, bad_wall, 6.0, 4.0, 0.0)
place_at(model, unnamed_door, 3.0, 0.0, 0.0)
place_at(model, proxy_obj, 9.0, 2.0, 3.0)

model.write("PRJ01-ARC-ZZ-01-M3-A-0001.ifc")
print("Generated IFC4 model with 3D spatial placements.")
