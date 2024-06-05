import math
import mathutils
import tempfile
import os

import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from smvp_ipc import *

from . import properties as props
from . import client
from .canvas import *
from .camera import *


# -------------------------------------------------------------------
#   Global data
# -------------------------------------------------------------------
scene_light_data = []
update_scene = False


# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------
class VIEW3D_OT_setupScene(Operator):
    bl_label ="Setup SMVP Scene"
    bl_id = "smvp.setup_scene"

class SMVP_CANVAS_OT_setCanvasActive(Operator):
    """Sets the selected canvas object active for actions in scene"""
    bl_label = "Set Active"
    bl_idname = "smvp_canvas.set_active"
    bl_description = "Set selected canvas object active in scene"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.smvp_canvas.is_canvas

    def execute(self, context):
        obj = context.object
        canvas = obj.smvp_canvas
        scn = context.scene

        # Set property 'sl_canvas' with selected canvas 
        if obj.smvp_canvas.is_canvas:
            scn.sl_canvas = obj
            return{'FINISHED'}

        self.report({"WARNING"}, f"No canvas object selected")
        return{'CANCELLED'}


class SMVP_CANVAS_OT_updateScene(Operator):
    """Updates lights and canvas positions for the SMVP server"""
    bl_label = "Update Scene"
    bl_idname = "smvp.update_scene"
    bl_description = "Updates lights and canvas positions for the SMVP server"

    def execute(self, context):
        #obj = context.object
        updateScene(context.scene)
        return{'FINISHED'}


class SMVP_CANVAS_OT_setDisplayMode(Operator):
    """Changing the display mode of the selected or active canvas"""
    bl_label = "Set display mode"
    bl_idname = "smvp_canvas.display_mode"
    bl_description = "Changing the display mode of the selected or active canvas"
    bl_options = {'REGISTER', 'UNDO'}

    display_mode: props.DisplayModeProp()
    
    @classmethod
    def poll(cls, context):
        return context.scene.sl_canvas is not None
    
    def execute(self, context):
        scn = context.scene
        obj = scn.sl_canvas
        canvas = obj.smvp_canvas
        
        # Stop receiving images for live mode
        client.serviceRemoveReq(canvas.canvas_texture)
        # For rendering mode set texture updated to false; TODO: Avoid re-rendering
        #if self.display_mode == 'rend':
        #    canvas_frame.texture_updated = False
        # Change of mode and scene update triggered by handler
        if canvas.display_mode != self.display_mode:
            canvas.display_mode = self.display_mode
        updateCanvas(scn, obj)
        return{'FINISHED'}


# TODO: OP for canvas object or globally? Can server handle object based render algorithms (probably not)?
class SMVP_CANVAS_OT_applyRenderAlgorithm(Operator):
    """Applys the selected render algorithm"""
    bl_label = "Apply Algorithm"
    bl_idname = "smvp_canvas.apply_algorithm"
    bl_description = "Applys the selected render algorithm"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return context.scene.sl_canvas is not None
    
    def execute(self, context):
        scn = context.scene
        obj = scn.sl_canvas
        canvas = obj.smvp_canvas
        
        # Send set renderer command
        message = Message(Command.SetRenderer, {'algorithm': scn.smvp_algorithms.algs_dropdown_items})
        client.sendMessage(message)
        # Update object
        setUpdateFlags(obj)
        updateScene(scn)
        return{'FINISHED'}


class SMVP_CANVAS_OT_updateEnv(Operator):
    """Updates the environment lighting for the rendering"""
    bl_label = "Update Environment"
    bl_idname = "smvp_canvas.update_env"
    bl_description = "Updates the environment lighting for the rendering"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return context.scene.sl_canvas is not None
    
    def execute(self, context):
        scn = context.scene
        obj = scn.sl_canvas
        updateEnvLighting(obj)
        message = Message(Command.LightsHdriTexture, {'path': obj.smvp_canvas.env_tex_path})
        client.sendMessage(message)
        updateCanvas(scn, obj)
        
        return{'FINISHED'}


class SMVP_CANVAS_OT_setGhostMode(Operator):
    bl_idname = "smvp_canvas.ghost_on"
    bl_label= "Show Ghostframes"
    bl_options = {'REGISTER'}
    
    

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        context.object.smvp_ghost.show_ghost = not context.object.smvp_ghost.show_ghost 
       
        updateCanvas(context.scene, context.object)
        
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
        mat = createCanvasMat(obj)
        obj.data.materials.append(mat)
        # Settings TODO only for EEVEE?
        mat.blend_method = 'HASHED'
        mat.shadow_method = 'HASHED'
        
        # Create image for live texture
        tex_name = f"smvp_{obj.smvp_canvas.canvas_id:02d}"
        ghosting_name = f"smvp_ghosting_{obj.smvp_canvas.canvas_id:02d}"
        resolution = scn.smvp_scene.resolution
        texture = bpy.data.images.new(tex_name, width=resolution[0], height=resolution[1], float_buffer=True)
        ghost = bpy.data.images.new(ghosting_name, width=resolution[0], height=resolution[1], float_buffer=True)
        obj.smvp_canvas.canvas_texture = texture.name
        obj.smvp_canvas.ghost_texture = ghost.name
                
        # Set active canvas object if current one is not available / not set
        if scn.sl_canvas is None:
            scn.sl_canvas = obj
        
        return {"FINISHED"}
    
    def invoke(self, context, event):
        return self.execute(context)


# -------------------------------------------------------------------
#   Event handlers
# -------------------------------------------------------------------
def frameChange(scene):
    updateTextures(scene)

def depthgraphUpdated(scene):
    global update_scene
    
    # Check if active canvas object is still valid and remove in case it isnt
    if scene.sl_canvas is not None and not scene.sl_canvas.name in scene.objects:
        scene.sl_canvas = None
    
    update_scene = True
    

def timerCallback():
    global update_scene
    scene = bpy.context.scene
    
    # Update active canvas (live or render) TODO: only send out calls when frames got received
    if scene.sl_canvas is not None:
        match scene.sl_canvas.smvp_canvas.display_mode:
            case 'rend':
                if update_scene:
                    # Update lights and update flags of canvases
                    updateScene(scene)
                    update_scene = False
            case 'live':
                updateCanvas(scene, scene.sl_canvas)
        
    return 1.0 / scene.smvp_scene.update_rate


# -------------------------------------------------------------------
#   Scene API and Helpers
# -------------------------------------------------------------------
def updateTextures(scene):
    """Function to call when current frame has changed"""
    #bpy.data.materials["Video"].node_tree.nodes["texture"].inputs[1].default_value = frame_numscene.frame_current
    for obj in bpy.data.objects:
        if obj.smvp_canvas.is_canvas:
            # Canvas found!
            updateCanvas(scene, obj)


def updateScene(scene, force_env_update=False):
    """Function to call when the scene has changed"""
    global scene_light_data
    
    if client.connected:
        # Check if environment map has been rendered
        if force_env_update or scene.sl_canvas.smvp_canvas.env_tex_path == '':
            updateEnvLighting(scene.sl_canvas)
            message = Message(Command.LightsHdriTexture, {'path': scene.sl_canvas.smvp_canvas.env_tex_path})
            client.sendMessage(message)
            updateCanvas(scene, scene.sl_canvas)
        
        # Get lights and check if anything has changed since last call
        new_lights = getLights()
        if len(new_lights) != len(scene_light_data) or new_lights != scene_light_data:
            # Assign light data
            scene_light_data = new_lights
            # Send to server
            message = Message(Command.LightsSet, scene_light_data)
            client.sendMessage(message)
        
            # Set update flags for all render textures of all canvases (TODO: or just active one?)
            #for obj in bpy.data.objects:
            #    if obj.smvp_canvas.is_canvas:
            #        setUpdateFlags(obj)
            if scene.sl_canvas is not None:
                setUpdateFlags(scene.sl_canvas)
        
            # Trigger image requests # TODO: Or just single canvas?
            #updateTextures(scene)
            updateCanvas(scene, scene.sl_canvas)
            
        # Otherwise only check for moved canvases and update these TODO: Server dosn't know about canvases and their transforms yet
        else:
            pass
            # updateCanvas(scene, canvas)
    


def setUpdateFlags(canvas_obj, preview=False):
    """Mark all frames as not updated"""
    for i in range(len(canvas_obj.smvp_canvas.frame_list)):
        canvas_obj.smvp_canvas.frame_list[i].texture_updated = False
        if preview:
            canvas_obj.smvp_canvas.frame_list[i].preview_updated = False
            


def getLights():
    #center_pos = canvas_obj.matrix_world.translation
    #canvas_rot = canvas_obj.rotation_euler.to_matrix().invert().to_4x4()
    #mat_transl_rot = 
    
    light_data = []
    for light in bpy.data.objects:
        if light.type == 'LIGHT' and light.visible_get(): # TODO: Hiding for renders (light.visible_get())
            power = float(light.data.energy) # multiplied with custom factor stop_lighting_factor
            color = list(light.data.color)# from_srgb_to_scene_linear() # convert ?
            pos = list(light.matrix_world.translation)
            dir = mathutils.Vector((0.0, 0.0, 1.0))
            dir.rotate(light.rotation_euler)
            
            match light.data.type:
                case 'SUN':
                    # Direction, angle, power, color
                    light_data.append({'type': 'sun', 'dir': list(dir), 'angle': light.data.angle, 'power': power/100, 'color': color})
                case 'POINT':
                    # Position, size, power, color
                    light_data.append({'type': 'point', 'pos': pos, 'size': light.data.shadow_soft_size, 'power': power/10, 'color': color})
                case 'SPOT':
                    # Position, rotation, size, power, color
                    light_data.append({'type': 'spot', 'pos': pos, 'dir': list(dir), 'angle': light.data.spot_size,\
                        'blend': light.data.spot_blend, 'size': light.data.shadow_soft_size, 'power': power/10, 'color': color})
                case 'AREA':
                    light_data.append({'type': 'area', 'pos': pos, 'dir': list(dir), 'angle': light.data.spread,\
                        'shape': light.data.shape, 'size': light.data.size, 'power': power/10, 'color': color})
                
    return light_data

def updateEnvLighting(canvas_obj):
    scn = bpy.context.scene
    smvp_scn = scn.smvp_scene
    
    # Find camera
    if not smvp_scn.render_cam in scn.objects:
        # create the first camera
        cam = bpy.data.cameras.new("SMVP Env Cam")
        cam.type = 'PANO'
        cam.panorama_type = 'EQUIRECTANGULAR'

        # create the first camera object
        cam_obj = bpy.data.objects.new("SMVP Env Cam", cam)
        cam_obj.location = (0,0,0)
        cam_obj.rotation_euler = (math.radians(90), 0, math.radians(180))
        bpy.context.collection.objects.link(cam_obj)
        cam_obj.hide_set(True) # hide_set?
        smvp_scn.render_cam = cam_obj.name
        
    env_cam = scn.objects[smvp_scn.render_cam]
        
    # Store render settings
    tmp_filepath = scn.render.filepath
    tmp_camera = scn.camera
    tmp_res = (scn.render.resolution_x, scn.render.resolution_y)
    tmp_engine = scn.render.engine
    tmp_img_settings = scn.render.image_settings
    tmp_threshold = scn.cycles.adaptive_threshold
    
    # Activate camera and set new settings
    canvas_obj.smvp_canvas.env_tex_path = os.path.join(tempfile.gettempdir(), f'{canvas_obj.name}_env_tex.exr')
    scn.render.filepath = canvas_obj.smvp_canvas.env_tex_path
    scn.camera = env_cam
    scn.render.resolution_x, scn.render.resolution_y = (1024, 512)
    scn.render.engine = 'CYCLES'
    scn.cycles.device = 'GPU'
    scn.cycles.adaptive_threshold = 0.1
    scn.render.image_settings.color_mode = 'RGB'
    scn.render.image_settings.file_format = 'OPEN_EXR'
    
    # Disable canvas, Render, enable again
    canvas_obj = True
    bpy.ops.render.render(write_still=True)
    canvas_obj = False
    
    # Reapply stored settings
    scn.render.filepath = tmp_filepath
    scn.camera = tmp_camera
    scn.render.resolution_x, scn.render.resolution_y = tmp_res
    scn.render.engine = tmp_engine
    scn.render.image_settings.color_mode = tmp_img_settings.color_mode
    scn.render.image_settings.file_format = tmp_img_settings.file_format
    scn.cycles.adaptive_threshold = tmp_threshold
    

# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    SMVP_CANVAS_OT_setCanvasActive,
    SMVP_CANVAS_OT_setDisplayMode,
    SMVP_CANVAS_OT_applyRenderAlgorithm,
    SMVP_CANVAS_OT_updateEnv,
    SMVP_CANVAS_OT_setGhostMode,
    SMVP_CANVAS_OT_updateScene,
    OBJECT_OT_smvpCanvasAdd,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Event handlers
    bpy.app.handlers.frame_change_pre.append(frameChange)
    bpy.app.handlers.depsgraph_update_post.append(depthgraphUpdated)
    bpy.app.timers.register(timerCallback)

    bpy.types.WindowManager.ghost_toggle = bpy.props.BoolProperty(default = False, update = update_ghost_func)    


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

