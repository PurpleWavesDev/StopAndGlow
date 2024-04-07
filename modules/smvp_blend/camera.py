import math
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from smvp_ipc import *

from . import properties as props
from . import client


# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------

class SMVP_CAMERA_OT_addLinked(Operator):
    """Add a new camera that is linked to the active canvas"""
    bl_idname = "smvp_camera.add_linked"
    bl_label = "Add linked camera"
    bl_description = "Add a new camera that is linked to the active canvas"
    bl_options = {'REGISTER', 'UNDO'}
    
    canvas_obj: props.StringProperty(
        name="Canvas Object",
        default="",
        description="Canvas Object to link to, leave empty to select active canvas")

    def execute(self, context):
        scn = context.scene
        
        # Create camera data and object
        cam_data = bpy.data.cameras.new("SMVP Camera")
        cam_obj = bpy.data.objects.new("SMVP Camera", cam_data)
        cam_obj.location = (0, -3, 0)
        cam_obj.rotation_euler = (math.pi/2, 0, 0)
        # Set properties
        if self.canvas_obj != "":
            cam_data.smvp.canvas_link = self.canvas_obj
        else:
            cam_data.smvp.canvas_link = scn.sl_canvas.name
        # Link to scene and set active
        scn.collection.objects.link(cam_obj)
        cam_obj.select_set(True)    
        context.view_layer.objects.active = cam_obj
        return {"FINISHED"}
        
    @classmethod
    def poll(cls, context):
        return context.scene.sl_canvas is not None




# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    SMVP_CAMERA_OT_addLinked,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

