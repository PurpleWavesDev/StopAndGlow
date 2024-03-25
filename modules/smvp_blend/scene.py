import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from smvp_ipc import *

from . import properties as props
from . import client


# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------
class VIEW3D_OT_setupScene(Operator):
    bl_label ="Setup SMVP Scene"
    bl_id = "smvpscene.setup"

    #return{'FINISHED'}



class SMVP_CANVAS_OT_setCanvasActive(Operator):
    """Sets the selected canvas object active for actions in scene"""
    bl_label = "Set Active"
    bl_idname = "smvp_canvas.activate_selected"
    bl_description = "Set selected canvas object active in scene"

    def execute(self, context):
        obj = context.object
        canvas = obj.smvp_canvas
        scn = context.scene

        if scn.smvp_scene.active_canvas is not obj.name:
            scn.smvp_scene.active_canvas = obj.name

        return{'FINISHED'}

# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    SMVP_CANVAS_OT_setCanvasActive,
    
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

