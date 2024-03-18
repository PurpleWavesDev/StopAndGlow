import bpy
import math
from bpy.props import IntProperty

from . import properties as props
#from . import client

## Operators
class OBJECT_OT_smvp_canvas_add(bpy.types.Operator):
    """Creates an canvas object"""

    bl_idname = "object.smvp_create_canvas"
    bl_label = "Creates an canvas object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_plane_add(rotation=(math.pi/2, 0, 0), size=2)
        canvas = bpy.context.object
        canvas.scale[0] = 16/9
        canvas.smvp_canvas.is_canvas = True
        return {"FINISHED"}
    
    def invoke(self, context, event):
        return self.execute(context)

## Events
def update_canvas_frame(scene):
    #bpy.data.materials["Video"].node_tree.nodes["texture"].inputs[1].default_value = frame_numscene.frame_current
    for obj in bpy.data.objects:
        if obj.smvp_canvas.is_canvas:
            obj['1'] = 0
            obj['2'] = 0
            obj['3'] = 0
            obj['4'] = 0


def register():
    # Operators
    bpy.utils.register_class(OBJECT_OT_smvp_canvas_add)
    
    # Events
    bpy.app.handlers.frame_change_pre.append(update_canvas_frame)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_smvp_canvas_add)
