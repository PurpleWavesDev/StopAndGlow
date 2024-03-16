import bpy
import math

from . import properties as props
#from . import client

class OBJECT_OT_smvp_canvas_add(bpy.types.Operator):
    """Creates an canvas object for the current frame"""

    bl_idname = "object.smvp_create_canvas"
    bl_label = "Creates an canvas object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_plane_add(rotation=(math.pi/2, 0, 0), size=2)
        canvas = bpy.context.object
        canvas.scale[0] = 16/9
        #canvas.data['smvp'] = bpy.props.PointerProperty(type=props.SmvpCanvasProps)
        return {"FINISHED"}
    
    def invoke(self, context, event):
        return self.execute(context)


def register():
    bpy.utils.register_class(OBJECT_OT_smvp_canvas_add)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_smvp_canvas_add)
