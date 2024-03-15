import bpy
from bpy.types import Scene, PropertyGroup
from bpy.props import *


class SmvpConfig(PropertyGroup):
    canvas: BoolProperty()

class SmvpCanvasProps(PropertyGroup):
    canvas: BoolProperty()


# This is where you assign any variables you need in your script
def register():
    # Property classes
    bpy.utils.register_class(SmvpConfig)
    Scene.smvp_config = bpy.props.PointerProperty(type=SmvpConfig)
    bpy.utils.register_class(SmvpCanvasProps)
    
    # Single properties
    Scene.my_property = BoolProperty(default=True)

def unregister():
    # Properties
    del Scene.smvp_config
    bpy.utils.unregister_class(SmvpConfig)
    bpy.utils.unregister_class(SmvpCanvasProps)
    
    # Single properties
    del Scene.my_property
