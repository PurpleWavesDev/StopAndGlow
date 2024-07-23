import math
import os
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList
import numpy as np
import cv2 as cv
import sng_ipc as ipc

from . import properties as props
from . import client

# -------------------------------------------------------------------
#   Ghosting
# -------------------------------------------------------------------
class SNG_CANVAS_OT_ghosting(Operator):
    """Show Ghostframes"""
    bl_idname = "object.show_ghostframes"
    bl_label = "Modal Show Ghostframes"
    
    @classmethod
    def poll(cls, context):
        return context.scene.sl_canvas is not None
    
    def execute(self, context):
        scn = context.scene
        obj = context.scene.sl_canvas
               
        obj.sng_ghost.show_ghost = True
        updateCanvas(scn, obj) #does this keep calling the fuction while true?
        return {'FINISHED'}

    def modal(self, context, event):
        obj = context.scene.sl_canvas
        obj.sng_ghost.show_ghost = True
        if not context.window_manager.ghost_toggle:
            obj.sng_ghost.show_ghost = False
            bpy.ops.sng_canvas.display_mode(display_mode=obj.display_mode)
            return {'FINISHED'}
           
        return {'PASS_THROUGH'}

    def invoke(self, context, event):         
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

def update_ghost_func(self, context):
    if self.ghost_toggle:
        bpy.ops.object.show_ghostframes('INVOKE_DEFAULT')
    return


# -------------------------------------------------------------------
#   Update functions / Canvas API
# -------------------------------------------------------------------
def updateCanvas(scene, obj):
    # Get texture to show
    img = getTexture(obj, scene.frame_current)
    
    if img is not None and obj.sng_ghost.show_ghost:
        frames= []
        keyframes = getKeyframes(obj)
        w,h = img.size
        key_img_data = np.zeros((w,h,4), 'f')
        prev_ghost_data = np.zeros((w,h,4), 'f')
        post_ghost_data = np.zeros((w,h,4), 'f')
        frame_img_data = None #space for array for current frame texture pixels
        ghost_img_data = None #space for array for final combined texture pixels
        opac1 = obj.sng_ghost.opacity # opacity from ui prop
        opac2 = 1 - opac1
        postghost = False
        preghost = False
        
        
        for i, key in reversed(list(enumerate(keyframes))): #count from latest keyframe to earliest, so the current frame can be cought
            getTextureForIdx(obj, i, display_mode='prev').pixels.foreach_get(key_img_data.ravel())
            
            if key[0] > scene.frame_current:
                postghost = True             
                if post_ghost_data.all() == 0: #if this is the first keyframe to be added, add to empty array 
                   post_ghost_data += key_img_data      
                else:
                    post_ghost_data = cv.addWeighted(key_img_data, opac1, post_ghost_data, opac2, 1.0) #add every keyframe behind current frame to a post ghost image, weighted with opacity as a factor
            
            else:
                if frame_img_data is None:
                    frame_img_data = np.zeros((w,h,4), 'f') 
                    img.pixels.foreach_get(frame_img_data.ravel()) # get either the keyframe directly on or, if there is none, the one before the current frame 

                elif prev_ghost_data.all() == 0:
                    prev_ghost_data += key_img_data #add next keyframe before current shown texture to empty array
                    preghost = True
                else:
                    prev_ghost_data = cv.addWeighted(key_img_data, opac1, prev_ghost_data, opac2, 1.0) # add the remaining previous keyframes weighted to array 

        
        if preghost:
            gray_prev = cv.cvtColor(prev_ghost_data, cv.COLOR_RGBA2GRAY)
            prev_ghost_data = np.dstack((gray_prev, np.zeros_like(gray_prev), np.zeros_like(gray_prev),np.ones_like(gray_prev)))
            prev_ghost_data = cv.addWeighted(prev_ghost_data, opac1, frame_img_data, opac2, 0.0)
            ghost_img_data = prev_ghost_data
        if postghost:
            gray_post = cv.cvtColor(post_ghost_data, cv.COLOR_RGBA2GRAY)
            post_ghost_data = np.dstack((np.zeros_like(gray_post),gray_post, np.zeros_like(gray_post),np.ones_like(gray_post)))
            post_ghost_data = cv.addWeighted(post_ghost_data, opac1, frame_img_data, opac2, 0.0)
            ghost_img_data = post_ghost_data
       

        if preghost and postghost:
            ghost_img_data= cv.addWeighted(prev_ghost_data, 0.5, post_ghost_data,0.5, 0.0)
        
        img = bpy.data.images[obj.sng_canvas.ghost_texture]
        img.pixels.foreach_set(ghost_img_data.ravel())

    try:
        obj.active_material.node_tree.nodes["ImageTexture"].image = img
    except Exception as e:
        print(f"Error setting canvas texture: {str(e)}")



# -------------------------------------------------------------------
#   Shader, Material, Image Texture Helpers
# -------------------------------------------------------------------
def createCanvasMat(obj):
    """Creates a new material for a canvas object"""
    # Create empty material
    mat = bpy.data.materials.new(name=f"canvas_{obj.sng_canvas.canvas_id:02d}_mat")
    mat.use_nodes = True
    mat.node_tree.nodes.remove(mat.node_tree.nodes['Principled BSDF'])

    # Create mix shader node and link with output
    mix = mat.node_tree.nodes.new('ShaderNodeMixShader')
    mix.location = 200,0
    matout = mat.node_tree.nodes.get('Material Output')
    matout.location = 400,0
    mat.node_tree.links.new(matout.inputs[0], mix.outputs[0])
    
    # Create transparency shader and link with mix shader
    trans = mat.node_tree.nodes.new('ShaderNodeBsdfTransparent')
    trans.location = 0,0
    mat.node_tree.links.new(mix.inputs[1], trans.outputs[0])
    
    # Create emission shader and value node and link with mix shader
    emission = mat.node_tree.nodes.new('ShaderNodeEmission')
    emission.location = 0,-150
    exposure = mat.node_tree.nodes.new('ShaderNodeValue')
    exposure.location = -200,-250
    mat.node_tree.links.new(mix.inputs[2], emission.outputs[0])
    mat.node_tree.links.new(emission.inputs[1], exposure.outputs[0])
    
    # Create image texture node and link with HSV
    img = mat.node_tree.nodes.new('ShaderNodeTexImage')
    img.location = -600,0
    img.name = "ImageTexture"
    mat.node_tree.links.new(emission.inputs[0], img.outputs[0])
    # Create color ramp to connect image alpha (depth mask?) with mix node
    ramp = mat.node_tree.nodes.new('ShaderNodeValToRGB') # ShaderNodeMapRange
    ramp.location = -200,300
    mat.node_tree.links.new(ramp.inputs[0], img.outputs[1])
    mat.node_tree.links.new(mix.inputs[0], ramp.outputs[0])
    
    # Create expression for exposure value
    fcurve = exposure.outputs[0].driver_add("default_value")
    # Driver
    d = fcurve.driver
    d.type = "AVERAGE"
    v = d.variables.new()
    v.name = "exposure"
    t = v.targets[0]
    t.id_type = 'OBJECT'
    t.id = obj
    t.data_path = '["exposure"]'

    return mat


def createFrameTextures(obj, index, resolution):
    """Creates textures for frame"""    
    item = obj.sng_canvas.frame_list[index]
    canvas_id = obj.sng_canvas.canvas_id
    frame_id = item.id

    # Create textures
    tex_name = f"sng_{canvas_id:02d}-{frame_id:04d}"
    prev_name = f"sng_prev_{canvas_id:02d}-{frame_id:04d}"
    texture = bpy.data.images.new(tex_name, width=resolution[0], height=resolution[1], float_buffer=True)
    preview = bpy.data.images.new(prev_name, width=resolution[0], height=resolution[1], float_buffer=True)
    
    # Add textures to frame list entry
    item.render_texture = texture.name
    item.preview_texture = preview.name


def getTexture(canvas_obj, frame):
    canvas = canvas_obj.sng_canvas
    
    # Live and baked lights
    if canvas.display_mode in ['live', 'baked']:
        # Start live capture with preview texture
        image_name = canvas.canvas_texture
        if image_name in bpy.data.images and client.connected:
            id = client.serviceAddReq(image_name)
            message = ipc.Message(ipc.Command.RequestCamera, {'id': id, 'mode': canvas.display_mode})
            client.sendMessage(message)    
            return bpy.data.images[image_name]
        return None

        
    if len(canvas.frame_list) == 0:
        # No frames in canvas
        return None
    
    # Find frame for current position in timeline
    index = 0 
    keyframes = getKeyframes(canvas_obj)
    for x, y in keyframes:
        if x > frame:
            break
        index += 1
    return getTextureForIdx(canvas_obj, max(0, index-1))


def getTextureForIdx(canvas_obj, index, display_mode=None):
    """Returns the texture for the index and display_mode. Uses active display mode if none provided""" 
    canvas = canvas_obj.sng_canvas
    canvas_frame = canvas.frame_list[index % len(canvas.frame_list)]
    # Get image name for display mode and check if image needs to be requested
    image_name = ""
    cmd_mode = None
    display_mode = canvas.display_mode if display_mode is None else display_mode
    match display_mode:
        case 'prev': # Preview
            image_name = canvas_frame.preview_texture
            # Request update if image has not been set
            if not canvas_frame.preview_updated:
                cmd_mode = "preview"
                canvas_frame.preview_updated = True
        case 'rend': # Render
            image_name = canvas_frame.render_texture
            # Request new image if it hasn't been updated or got replaced TODO?!
            if not canvas_frame.texture_updated:
                cmd_mode = "render"
                canvas_frame.texture_updated = True
    
    # If image is not valid, create a new one and call function recursively
    if not image_name in bpy.data.images:
        if image_name != "":
            print(f"Error: Image {image_name} missing")
            createFrameTextures(canvas_obj, index, bpy.context.scene.sng_scene.resolution)
            getTextureForIdx(canvas_obj, index, display_mode)
    
    # If command is set, generate ID for requested image and send request
    if cmd_mode is not None:
        id = client.serviceAddReq(image_name)
        message = ipc.Message(ipc.Command.RequestSequence, {'mode': cmd_mode, 'id': id, 'path': canvas_frame.seq_path})
        client.sendMessage(message)    
    
    # Return texture
    return bpy.data.images[image_name]


def getKeyframes(obj, data_path='["frame_keys"]'):
    try:
        fc = obj.animation_data.action.fcurves.find('["frame_keys"]')
        fc.update()
        return [keyframe.co for keyframe in fc.keyframe_points]
    except:
        return []


def rgb2_lumin_grey(orig_img):
    luminosity_constant = [0.21,0.72,0.07]
    return np.dot(orig_img[...,3], luminosity_constant).astype(np.uint8)



# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    SNG_CANVAS_OT_ghosting,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


