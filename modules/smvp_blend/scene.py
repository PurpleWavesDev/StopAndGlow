import math
import mathutils
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

   



class SMVP_CANVAS_OT_setCanvasActive(Operator):
    """Sets the selected canvas object active for actions in scene"""
    bl_label = "Set Active"
    bl_idname = "smvp_canvas.activate_selected"
    bl_description = "Set selected canvas object active in scene"

    def execute(self, context):
        obj = context.object
        canvas = obj.smvp_canvas
        scn = context.scene

        # fill property 'active_canvas' with name of selected canvas 
        if scn.smvp_scene.active_canvas is not obj.name:
            if obj.smvp_canvas.is_canvas:
                scn.smvp_scene.active_canvas= obj.name

        return{'FINISHED'}

class SMVP_CANVAS_OT_updateScene(Operator):
    """Updates lights and canvas positions for the SMVP server"""
    bl_label = "Updates scene"
    bl_idname = "smvp.update_scene"
    bl_description = "Updates lights and canvas positions for the SMVP server"

    def execute(self, context):
        obj = context.object
        updateScene(obj)
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
        bpy.ops.mesh.primitive_plane_add(size=1)
        obj = bpy.context.object
        scn = context.scene
        
        # Properties
        obj.name = "Canvas"
        obj.smvp_canvas.is_canvas = True
        obj['exposure'] = 1.0
        #canvas['exposure_preview'] = 1.0
        obj['frame_keys'] = True
        # Apply rotation and scale
        rotation=mathutils.Euler((math.pi/2, 0, 0), obj.rotation_mode)
        scale=(1, 9.0/16.0, 1)
        matrix = mathutils.Matrix.LocRotScale(None, rotation, scale)
        obj.data.transform(matrix)
        
        # Set ID and increment
        obj.smvp_canvas.canvas_id = scn.smvp_scene.canvas_ids
        scn.smvp_scene.canvas_ids += 1
        
        # Set material, create slot and assign
        mat = canvas.createCanvasMat(obj)
        obj.data.materials.append(mat)
        # Settings TODO only for EEVEE?
        mat.blend_method = 'HASHED'
        mat.shadow_method = 'HASHED'
        
        # Create image for live texture
        tex_name = f"smvp_{obj.smvp_canvas.canvas_id:02d}"
        resolution = scn.smvp_scene.resolution
        texture = bpy.data.images.new(tex_name, width=resolution[0], height=resolution[1], float_buffer=True)
                
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

def updateScene(obj):
    if client.connected:
        # Get lights and send to server
        light_data = getLights(obj)
        Message(Command.LightsSet, light_data)
        client.sendMessage(message)
        
        # Mark rendered frames as not updated
        for obj in bpy.data.objects:
            if obj.smvp_canvas.is_canvas:
                for i in range(len(obj.smvp_canvas.frame_list)):
                    obj.smvp_canvas.frame_list[i].updated = False
        
# -------------------------------------------------------------------
#   Helpers
# -------------------------------------------------------------------
def getLights(canvas_obj):
    center_pos = canvas_obj.matrix_world.translation
    #canvas_rot = canvas_obj.rotation_euler.to_matrix().invert().to_4x4()
    #mat_transl_rot = 
    
    light_data = {'point': [], 'sun': []}
    for light in bpy.data.objects:
        if light.type == 'LIGHT':
            match light.data.type:
                case 'POINT':
                    # Relative position (factoring in scale), size(?), power, color
                    relative_pos = light.matrix_world.translation - center_pos
                    # Rotate with canvas rotation
                    #relative_pos.rotate(canvas_rot)
                    # Scale by canvsa scale
                    #relative_pos *= scale
                    power = light.data.energy # multiplied with custom factor stop_lighting_factor
                    color = light.data.color# from_srgb_to_scene_linear() # convert ?
                    light_data['point'].append({'position': relative_pos, 'power': power, 'color': (color.r, color.g, color.b)})
                case 'SUN':
                    # Direction, spread(?), power, color
                    vec = mathutils.Vector((0.0, 0.0, 1.0))
                    vec.rotate(light.rotation_euler)
                    latlong = (math.degrees(math.asin(vec[2])), math.degrees(math.acos(vec[1])) if vec[0] > 0 else 360 - math.degrees(math.acos(vec[1]))) # TODO
                    power = light.data.energy # multiplied with custom factor stop_lighting_factor
                    color = light.data.color# from_srgb_to_scene_linear() # convert ?
                    light_data['sun'].append({'latlong': latlong, 'power': power, 'color': (color.r, color.g, color.b)})
                case 'SPOT':
                    pass
                case 'AREA':
                    pass
    
    return light_data


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

