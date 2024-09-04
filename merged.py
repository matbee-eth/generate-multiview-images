import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Matrix
from PIL import Image

def import_stl(filepath):
    bpy.ops.wm.stl_import(filepath=filepath)
    imported_objects = bpy.context.selected_objects
    if not imported_objects:
        raise ValueError("No objects were imported from the STL file.")
    return imported_objects

def setup_material(obj):
    if not obj.data.materials:
        material = bpy.data.materials.new(name=f"Material_{obj.name}")
        obj.data.materials.append(material)
    else:
        material = obj.data.materials[0]

    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    nodes.clear()

    node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
    node_diffuse.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)  # Light gray

    node_output = nodes.new(type='ShaderNodeOutputMaterial')

    links.new(node_diffuse.outputs['BSDF'], node_output.inputs['Surface'])

def separate_loose_parts(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    return bpy.context.selected_objects

def get_scene_bounding_box(objects):
    bbox_corners = []
    for obj in objects:
        bbox_corners.extend([obj.matrix_world @ Vector(corner) for corner in obj.bound_box])
    
    bbox_min = Vector(map(min, zip(*bbox_corners)))
    bbox_max = Vector(map(max, zip(*bbox_corners)))
    return bbox_min, bbox_max

def setup_camera_for_view(camera, objects, view):
    bbox_min, bbox_max = get_scene_bounding_box(objects)
    dimensions = bbox_max - bbox_min
    center = (bbox_max + bbox_min) / 2

    # Add padding
    padding_factor = 1.1
    dimensions *= padding_factor
    
    if view == "X+":
        cam_pos = Vector((bbox_max.x + dimensions.x, center.y, center.z))
    elif view == "X-":
        cam_pos = Vector((bbox_min.x - dimensions.x, center.y, center.z))
    elif view == "Y+":
        cam_pos = Vector((center.x, bbox_max.y + dimensions.y, center.z))
    elif view == "Y-":
        cam_pos = Vector((center.x, bbox_min.y - dimensions.y, center.z))
    elif view == "Z+":
        cam_pos = Vector((center.x, center.y, bbox_max.z + dimensions.z))
    elif view == "Z-":
        cam_pos = Vector((center.x, center.y, bbox_min.z - dimensions.z))

    camera.location = cam_pos
    direction = center - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()

    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(dimensions)

    # Ensure clipping planes encompass all objects
    max_dimension = max(dimensions)
    camera.data.clip_start = 0.1
    camera.data.clip_end = max_dimension * 2

    print(f"Camera position for {view} view: {camera.location}")
    print(f"Camera rotation for {view} view: {camera.rotation_euler}")
    print(f"Camera ortho scale for {view} view: {camera.data.ortho_scale}")


def setup_lighting():
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    
    light_setups = [
        ("Light 1", 'SUN', (math.radians(45), math.radians(45), math.radians(45)), 0.5),
        ("Light 2", 'SUN', (math.radians(45), math.radians(-45), math.radians(-45)), 0.5),
        ("Light 3", 'SUN', (math.radians(-45), math.radians(45), math.radians(45)), 0.5),
        ("Light 4", 'SUN', (math.radians(-45), math.radians(-45), math.radians(-45)), 0.5),
        # ("Light 5", 'SUN', (math.radians(90), 0, 0), 0.5),
        # ("Light 6", 'SUN', (math.radians(-90), 0, 0), 0.5),
        ("Light 7", 'SUN', (math.radians(135), 0, 0), 0.5)  # Bottom light
    ]

    for name, type, rotation, energy in light_setups:
        light_data = bpy.data.lights.new(name=name, type=type)
        light_object = bpy.data.objects.new(name=name, object_data=light_data)
        bpy.context.collection.objects.link(light_object)
        light_object.rotation_euler = rotation
        light_data.energy = energy

def setup_scene_for_rendering():
    world = bpy.context.scene.world
    world.use_nodes = True
    world_nodes = world.node_tree.nodes
    world_links = world.node_tree.links
    
    world_nodes.clear()
    
    node_background = world_nodes.new(type='ShaderNodeBackground')
    node_background.inputs[0].default_value = (1, 1, 1, 0)  # RGBA all 0 for full transparency
    node_background.inputs[1].default_value = 0  # Strength 0
    
    node_output = world_nodes.new(type='ShaderNodeOutputWorld')
    
    world_links.new(node_background.outputs[0], node_output.inputs[0])
    
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.render.image_settings.color_mode = 'RGBA'
    
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 128

    bpy.context.scene.world.cycles_visibility.camera = True

def render_image(filepath, camera):
    bpy.context.scene.camera = camera
    bpy.context.scene.render.filepath = filepath
    bpy.context.scene.render.resolution_x = 1024
    bpy.context.scene.render.resolution_y = 1024
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.image_settings.color_mode = 'RGBA'
    bpy.ops.render.render(write_still=True)

def get_bounding_box(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

def get_model_primary_axis(objects):
    bbox_corners = []
    for obj in objects:
        bbox_corners.extend([obj.matrix_world @ Vector(corner) for corner in obj.bound_box])
    
    bbox_min = Vector(map(min, zip(*bbox_corners)))
    bbox_max = Vector(map(max, zip(*bbox_corners)))
    dimensions = bbox_max - bbox_min

    max_dim = max(dimensions)
    if max_dim == dimensions.x:
        return 0  # X-axis
    elif max_dim == dimensions.y:
        return 1  # Y-axis
    else:
        return 2  # Z-axis

def get_object_bounds(obj):
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_corner = Vector(map(min, zip(*bbox)))
    max_corner = Vector(map(max, zip(*bbox)))
    return min_corner, max_corner

def create_bounding_box_object(name, bounds):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)

    bpy.context.collection.objects.link(obj)

    # Create mesh from bounds
    verts = bounds
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom face
        (4, 5), (5, 6), (6, 7), (7, 4),  # Top face
        (0, 4), (1, 5), (2, 6), (3, 7)   # Connecting edges
    ]
    mesh.from_pydata(verts, edges, [])

    # Update mesh with new data
    mesh.update()

    # Set display type to wire
    obj.display_type = 'WIRE'

    return obj

def arrange_parts(parts, spacing=0.1):
    bpy.ops.object.select_all(action='DESELECT')
    
    primary_axis = get_model_primary_axis(parts)
    print(f"Primary axis determined: {primary_axis}")

    # Get bounding boxes and sort parts
    part_bounds = [(obj, *get_object_bounds(obj)) for obj in parts]
    sorted_parts = sorted(part_bounds, key=lambda x: x[1][primary_axis])

    bounding_boxes = []
    current_pos = 0

    for obj, min_corner, max_corner in sorted_parts:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Calculate offset to align with current_pos
        offset = current_pos - min_corner[primary_axis]
        
        # Move object
        if primary_axis == 0:  # X-axis
            obj.location.x += offset
        elif primary_axis == 1:  # Y-axis
            obj.location.y += offset
        else:  # Z-axis
            obj.location.z += offset

        # Update current_pos for next object
        current_pos = max_corner[primary_axis] - min_corner[primary_axis] + current_pos + spacing

        # Update object's world matrix
        bpy.context.view_layer.update()

        # Create bounding box visualization
        bbox_obj = create_bounding_box_object(f"{obj.name}_bbox", get_bounding_box(obj))
        bbox_obj.parent = obj
        bounding_boxes.append(bbox_obj)

    # Center the arrangement
    total_length = current_pos - spacing
    center_offset = -total_length / 2

    for obj in parts:
        if primary_axis == 0:
            obj.location.x += center_offset
        elif primary_axis == 1:
            obj.location.y += center_offset
        else:
            obj.location.z += center_offset

    # Final update to ensure all transformations are applied
    bpy.context.view_layer.update()

    return bounding_boxes, primary_axis

def process_stl(stl_path, output_dir):
    # Clear existing mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.delete()

    # Import STL
    imported_objects = import_stl(stl_path)

    # Separate loose parts
    all_parts = []
    for obj in imported_objects:
        parts = separate_loose_parts(obj)
        all_parts.extend(parts)

    # Setup materials
    for obj in all_parts:
        setup_material(obj)

    # Arrange parts
    bounding_boxes, primary_axis = arrange_parts(all_parts)
    print(f"Arranged parts along {primary_axis} axis")

    # Setup lighting and scene
    setup_lighting()
    setup_scene_for_rendering()

    # Create camera
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    bpy.context.scene.collection.objects.link(camera)

    # Define views and their corresponding file names
    views = ["X+", "X-", "Y+", "Y-", "Z+", "Z-"]
    view_names = {
        0: ["back_view.png", "front_view.png",  "right_view.png", "left_view.png", "top_view.png", "bottom_view.png"],
        1: ["right_view.png", "left_view.png", "back_view.png", "front_view.png", "top_view.png", "bottom_view.png"],
        2: ["top_view.png", "bottom_view.png", "right_view.png", "left_view.png", "back_view.png", "front_view.png"]
    }

    # Render views
    for view, file_name in zip(views, view_names[primary_axis]):
        setup_camera_for_view(camera, all_parts, view)
        render_image(os.path.join(output_dir, file_name), camera)

    return primary_axis

def crop_transparency(image):
    alpha = image.split()[-1]
    bbox = alpha.getbbox()
    return image.crop(bbox) if bbox else image

def resize_image(image, max_size):
    ratio = min(max_size[0] / image.width, max_size[1] / image.height)
    return image.resize((int(image.width * ratio), int(image.height * ratio)), Image.LANCZOS)

def assemble_multi_view_image(main_image_path, view_image_paths, output_path):
    # Create a new blank image with white background
    result = Image.new('RGBA', (2048, 2048), (255, 255, 255, 255))

    # Open and resize the main image
    main_image = Image.open(main_image_path).convert("RGBA")
    main_image = resize_image(main_image, (1024, 512))

    # Paste the main image
    result.paste(main_image, (512, 0), main_image)

    # Open the view images
    view_images = [crop_transparency(Image.open(path).convert("RGBA")) for path in view_image_paths]

    # Define positions and sizes for each view
    layout = [
        ((0, 512), (512, 512)),     # top-left
        ((0, 1024), (512, 512)),    # bottom-left
        ((1536, 512), (512, 512)),  # top-right
        ((0, 1536), (512, 256)),    # bottom-left
        ((512, 1024), (256, 1024)), # center
        ((1536, 1536), (512, 256)), # bottom-right
    ]

    # Paste the view images
    for img, (pos, size) in zip(view_images, layout):
        resized_img = resize_image(img, size)
        result.paste(resized_img, pos, resized_img)

    # Save the result
    result.save(output_path, 'PNG')
    print(f"Multi-view image saved to {output_path}")
def process_directory(base_path):
    for dir_name in os.listdir(base_path):
        dir_path = os.path.join(base_path, dir_name)
        if not os.path.isdir(dir_path):
            continue

        file_dir = os.path.join(dir_path, "File")
        if not os.path.exists(file_dir):
            file_dir = os.path.join(dir_path, "Files")
        if not os.path.exists(file_dir):
            print(f"No File or Files directory found in {dir_path}")
            continue

        img_dir = os.path.join(dir_path, "IMG")
        if not os.path.exists(img_dir):
            print(f"No IMG directory found in {dir_path}")
            continue

        # Find STL files
        stl_files = [f for f in os.listdir(file_dir) if f.endswith('.stl') and 'keychain' not in f.lower()]
        if not stl_files:
            print(f"No valid STL files found in {file_dir}")
            continue

        # Process each STL file
        for stl_file in stl_files:
            stl_path = os.path.join(file_dir, stl_file)
            primary_axis = process_stl(stl_path, file_dir)

        # Find main image
        main_image_files = sorted([f for f in os.listdir(img_dir) if f.endswith('.png') and f[0].isdigit()])
        if not main_image_files:
            print(f"No main image found in {img_dir}")
            continue
        main_image_path = os.path.join(img_dir, main_image_files[0])

        # Define view image paths
        view_image_paths = [
            os.path.join(file_dir, 'front_view.png'),
            os.path.join(file_dir, 'back_view.png'),
            os.path.join(file_dir, 'left_view.png'),
            os.path.join(file_dir, 'right_view.png'),
            os.path.join(file_dir, 'top_view.png'),
            os.path.join(file_dir, 'bottom_view.png')
        ]

        view_image_paths = [path for path in view_image_paths if os.path.exists(path)]

        if len(view_image_paths) < 6:
            print(f"Warning: Not all view images found in {file_dir}")

        output_path = os.path.join(dir_path, 'assembled_multi_view.png')
        assemble_multi_view_image(main_image_path, view_image_paths, output_path)

def main():
    base_path = "/mnt/data/zou3d"  # Replace with your actual base path
    process_directory(base_path)

if __name__ == "__main__":
    main()