import bpy
from bpy import context
from mathutils import Euler, Vector
import json
import os
import numpy as np
import math

CALIBRATION_FILE = "./data/calibration/lightdome.json"
COLLECTION_NAME = "Domelights"

def create_lights(path):
    light_data = bpy.data.lights.new(name="domelight", type='SPOT')
    light_data.energy = 5000
    light_data.spot_blend = 0
    light_data.cutoff_distance = 1.0
    
    with open(path, "r") as file:
        data = json.load(file)
        for light in data['lights']:
            if 'xyz' in light:
                insert_light(int(light['id']), light_data, light['xyz'])


def insert_light(id, light_data, position):
    # Create new object, pass the light data 
    light_object = bpy.data.objects.new(name=f"{id:03d}_domelight", object_data=light_data)

    # Link object to collection in context
    if not COLLECTION_NAME in bpy.data.collections:
        col = bpy.data.collections.new(COLLECTION_NAME)
        context.scene.collection.children.link(col)
        
    bpy.data.collections[COLLECTION_NAME].objects.link(light_object)

    # Change light position, scale and rotation
    position = Vector(position)
    light_object.location = position * 10
    light_object.scale = (0.05, 0.05, 0.05)
    # Calculate rotation
    rotation = Vector(-position)
    angle_XZ = math.atan2(rotation[0],rotation[2]) + math.pi
    # Rotate on plane that is projected of the YZ-Plane rotated around XZ-angle (XZ-angle-Y-Plane)
    # Rotate vector minus XZ angle and read 
    rotation.rotate(Euler([0, -angle_XZ, 0]))
    angle_Z_XZ = math.atan2(rotation[2], rotation[1]) + math.pi/2
    light_object.rotation_euler = Euler([angle_Z_XZ, angle_XZ, 0])
    
    # Set Key for current ID
    cur_frame = id
    light_object.keyframe_insert(data_path="hide_viewport", frame=cur_frame)
    light_object.keyframe_insert(data_path="hide_render", frame=cur_frame)
    # Disable for other frames
    light_object.hide_viewport = light_object.hide_render = True
    light_object.keyframe_insert(data_path="hide_viewport", frame=cur_frame+1)
    light_object.keyframe_insert(data_path="hide_render", frame=cur_frame+1)
    light_object.keyframe_insert(data_path="hide_viewport", frame=cur_frame-1)
    light_object.keyframe_insert(data_path="hide_render", frame=cur_frame-1)
    
    light_object.update_tag()


def print(*args, **kwargs):
    override = get_context("CONSOLE")
    with context.temp_override(**override):
        s = " ".join([str(arg) for arg in args])
        for line in s.split("\n"):
            bpy.ops.console.scrollback_append(text=line, type='OUTPUT')

def get_context(type):
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == type:
                context_override = {"area": area, "screen": screen}
                return context_override


if __name__ == "__main__":
    create_lights(CALIBRATION_FILE)