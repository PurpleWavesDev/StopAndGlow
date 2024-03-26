import math
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from smvp_ipc import *

from . import properties as props
from . import client
from . import canvas
from . import camera


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
#   Object creation Operators
# -------------------------------------------------------------------
class OBJECT_OT_smvpCanvasAdd(bpy.types.Operator):
    """Creates an canvas object"""
    
    bl_idname = "object.smvp_canvas_add"
    bl_label = "Creates an canvas object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Add primitive
        bpy.ops.mesh.primitive_plane_add(rotation=(math.pi/2, 0, 0), size=2)
        obj = bpy.context.object
        scn = context.scene
        
        # Properties
        obj.name = "Canvas"
        obj.scale[0] = 16/9
        obj.smvp_canvas.is_canvas = True
        obj['exposure'] = 1.0
        #canvas['exposure_preview'] = 1.0
        obj['frame_keys'] = True
        
        # Set ID and increment
        obj.smvp_canvas.canvas_id = scn.smvp_scene.canvas_ids
        scn.smvp_scene.canvas_ids += 1
        
        # Set material, create slot and assign
        mat = canvas.createCanvasMat(obj)
        obj.data.materials.append(mat)
        # Settings TODO only for EEVEE?
        mat.blend_method = 'HASHED'
        mat.shadow_method = 'HASHED'
                
        # Set active canvas object if current one is not available / not set
        if not scn.smvp_scene.active_canvas in bpy.data.objects:
            scn.smvp_scene.active_canvas = obj.name
        
        return {"FINISHED"}
    
    def invoke(self, context, event):
        return self.execute(context)




# -------------------------------------------------------------------
#   Event handlers
# -------------------------------------------------------------------
def update_canvas_textures(scene):
    #bpy.data.materials["Video"].node_tree.nodes["texture"].inputs[1].default_value = frame_numscene.frame_current
    for obj in bpy.data.objects:
        if obj.smvp_canvas.is_canvas:
            # Canvas found!
            canvas.update_single_canvas_tex(scene, obj)
            

# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    SMVP_CANVAS_OT_setCanvasActive,
    OBJECT_OT_smvpCanvasAdd,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Event handlers
    bpy.app.handlers.frame_change_pre.append(update_canvas_textures)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

