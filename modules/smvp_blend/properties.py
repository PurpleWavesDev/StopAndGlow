import bpy
from bpy.types import Scene, PropertyGroup
from bpy.props import *

  
class SmvpConfig(PropertyGroup):
    is_canvas: BoolProperty(default=False, name="Is Canvas")

class SmvpCanvasProps(PropertyGroup):
    is_canvas: BoolProperty()


# This is where you assign any variables you need in your script
def register():
    # Property classes
    bpy.utils.register_class(SmvpConfig)
    Scene.smvp_config = bpy.props.PointerProperty(type=SmvpConfig, name="SMVP Configuration")
    bpy.utils.register_class(SmvpCanvasProps)
    bpy.types.Object.smvp_canvas = bpy.props.PointerProperty(type=SmvpCanvasProps, name="SMVP Canvas")
    
    # Single properties
    Scene.my_property = BoolProperty(default=True)

def unregister():
    # Properties
    del Scene.smvp_config
    bpy.utils.unregister_class(SmvpConfig)
    bpy.utils.unregister_class(SmvpCanvasProps)
    
    # Single properties
    del Scene.my_property
