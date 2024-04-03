import math
import os
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

import smvp_ipc as ipc

from . import properties as props
from . import client

DEFAULT_RESOULTION = (1920, 1080)

# -------------------------------------------------------------------
#   Frame UI List Operators
# -------------------------------------------------------------------

class SMVP_CANVAS_OT_overrideConfirm(Operator):
    """Override current frame?"""
    bl_idname = "smvp_canvas.override_confirm"
    bl_label = "Override current frame?"
    bl_options = {'REGISTER', 'INTERNAL'}

    capture: BoolProperty(name="Call capture instead of add", default=False)
    
    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        # Call operator again with override set
        if capture:
            bpy.ops.smvp_canvas.capture('INVOKE_DEFAULT', override=True)
        else:
            bpy.ops.smvp_canvas.frame_add('INVOKE_DEFAULT', override=True)
        return {'FINISHED'}
    
class SMVP_CANVAS_OT_addFrame(Operator):
    """Add new frame from sequence folder"""
    bl_idname = "smvp_canvas.frame_add"
    bl_label = "Load Sequence"
    bl_description = "Add new frame from sequence folder"
    bl_options = {'REGISTER'}
    
    directory: StringProperty(
        name="Sequence Path",
        description="Path to load the Sequence Data from"
        )
    override: BoolProperty(
        default=False,
        name="Override current frame",
        description="If set, operator will delete current frame and replace it with the new frame"
        )

    def invoke(self, context, event):
        # Add new sequence as frame entry
        obj = context.object
        scn = context.scene
        
        if not self.override:
            # Check if there is a keyframe already that would be overwritten
            keyframes = getKeyframes(obj)
            for x, y in keyframes:
                if x == scn.frame_current:
                    bpy.ops.smvp_canvas.override_confirm('INVOKE_DEFAULT')
                    return {'RUNNING_MODAL'}

        # Open browser, will write selected path into our directory property
        context.window_manager.fileselect_add(self)
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}

    def execute(self, context):
        obj = context.object
        scn = context.scene
        canvas = obj.smvp_canvas
        #idx = canvas.frame_list_index
                
        # Check if directory is a valid folder
        if os.path.isdir(self.directory):
            keyframes = getKeyframes(obj)
            new_index = 0
            # Iterate over keys, increment index count and delete entry if there is one for the current frame
            for x, y in keyframes:
                if x == scn.frame_current:
                    # Remove item (on index keys_before) and delete current keyframe
                    deleteFrameEntry(obj, new_index)
                    break
                if x > scn.frame_current:
                    break
                new_index += 1

            # Create new item
            item = canvas.frame_list.add()
            num_items = len(canvas.frame_list)
            # Index shall not be greater then item count
            new_index = min(new_index, len(canvas.frame_list)-1)
            
            # Assign path and name
            item.seq_path = os.path.normpath(self.directory)
            item.name = os.path.basename(item.seq_path)
    
            # Set Frame ID and increment
            frame_id = item.id = canvas.frame_ids
            canvas.frame_ids += 1
            
            # Move to correct place. Assign all values to item before, won't change position after move!
            if new_index != num_items-1:
                canvas.frame_list.move(num_items-1, new_index)
            canvas.frame_list_index = new_index

            # Create texture images
            createFrameTextures(obj, new_index, scn.smvp_scene.resolution)
            
            # Insert keyframe
            obj.keyframe_insert(data_path='["frame_keys"]')
            
            # Send load command
            message = ipc.Message(ipc.Command.LoadFootage, {'path': self.directory})
            client.sendMessage(message)
            context.area.tag_redraw()
            
            # Update texture
            update_single_canvas_tex(context.scene, obj)
            return {"FINISHED"}
            
        else:
            self.report({'WARNING'}, "Not a valid folder")
            return {"CANCELLED"}

      


class SMVP_CANVAS_OT_actions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "smvp_canvas.frame_action"
    bl_label = "Frame List Actions"
    bl_description = "Move frame items up and down, add and remove"
    bl_options = {'REGISTER'}

    action: EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", "")))

    @classmethod
    def poll(cls, context):
        return len(context.object.smvp_canvas.frame_list) > 0
    
    def invoke(self, context, event):
        obj = context.object
        idx = obj.smvp_canvas.frame_list_index
        
        try:
            item = obj.smvp_canvas.frame_list[idx]
        except IndexError:
            pass
        else:
            if self.action == 'DOWN' and idx < len(obj.smvp_canvas.frame_list) - 1:
                item_next = obj.smvp_canvas.frame_list[idx+1].name
                obj.smvp_canvas.frame_list.move(idx, idx+1)
                obj.smvp_canvas.frame_list_index += 1
                info = 'Frame "%s" moved to position %d' % (item.name, obj.smvp_canvas.frame_list_index + 1)
                self.report({'INFO'}, info)

            elif self.action == 'UP' and idx >= 1:
                item_prev = obj.smvp_canvas.frame_list[idx-1].name
                obj.smvp_canvas.frame_list.move(idx, idx-1)
                obj.smvp_canvas.frame_list_index -= 1
                info = 'Frame "%s" moved to position %d' % (item.name, obj.smvp_canvas.frame_list_index + 1)
                self.report({'INFO'}, info)

            elif self.action == 'REMOVE':
                info = 'Frame "%s" removed from list' % (obj.smvp_canvas.frame_list[idx].name)
                deleteFrameEntry(obj, idx)
                if obj.smvp_canvas.frame_list_index >= idx:
                    obj.smvp_canvas.frame_list_index -= 1
                self.report({'INFO'}, info)
            
        update_single_canvas_tex(context.scene, obj)
        return {"RUNNING_MODAL"}


class SMVP_CANVAS_OT_ghosting(Operator):
    """Show Ghostframes"""
    bl_idname = "object.ghost_modal"
    bl_label = "Modal Show Ghostframes"
    
    def execute(self, context):
        #probably don't need this one
        return {'FINISHED'}

    def modal(self, context, event):
        # textur anzeigen, aber nicht immer neu berechnen
        # if ghostframe not none for current frame make ghostframe
        # wie behalte ich die frametexturen im cache, so dass ich eine animation zeigen kann?
        # update button zum neu berechnen?   

        if not context.window_manager.ghost_toggle:
            # stop when False 
            # turn display mode back to before
            self.report({'INFO'}, "done")
            return {'FINISHED'}

        self.report({'INFO'}, "passthrough")    
        return {'PASS_THROUGH'}#passthrough so blender still works 

    def invoke(self, context, event): #just for listening for events??
        # maybe start the ghost mode here?
        self.report({'INFO'}, "invoke")
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

def update_ghost_func(self, context):
    if self.ghost_toggle:
        bpy.ops.object.ghost_modal('INVOKE_DEFAULT')
    return


class SMVP_CANVAS_OT_capture(Operator):
    """Capture frame data for rendering or with baked lighting"""
    bl_idname = "smvp_canvas.capture"
    bl_label = "Capture"
    bl_description = "Capture frame data for rendering or with baked lighting"
    bl_options = {'REGISTER'}
    
    baked: BoolProperty(name="Capture with baked lights", default=False)
    name: StringProperty(
        name="Sequence name",
        description="Name of sequence, date and time is used if empty"
        )
    override: BoolProperty(
        default=False,
        name="Override current frame",
        description="If set, operator will delete current frame and replace it with the captured frame"
        )

    def invoke(self, context, event):
        # Add new sequence as frame entry
        obj = context.object
        scn = context.scene
        
        if not self.override:
            # Check if there is a keyframe already that would be overwritten
            keyframes = getKeyframes(obj)
            for x, y in keyframes:
                if x == scn.frame_current:
                    bpy.ops.smvp_canvas.override_confirm('INVOKE_DEFAULT', capture=True)
                    return {'RUNNING_MODAL'}

        # Execute capture command
        return execute()
    
    def execute(self, context):
        obj = context.object
        tex = obj.smvp_canvas.frame_list[0].preview_texture
        
        id = client.serviceAddReq(tex)
        # Send capture message
        message = None
        if self.baked:
            message = ipc.Message(ipc.Command.CaptureBaked, {'id': id, 'name': self.name})
        else:
            message = ipc.Message(ipc.Command.CaptureLights, {'id': id, 'name': self.name})
        answer = client.sendMessage(message)
        
        if answer.command == ipc.Command.CommandProcessing:
            # Add frame to list
            bpy.ops.smvp_canvas.frame_add(directory=answer.data['path'], override=True)
            return{'FINISHED'}

        self.report({'WARNING'}, f"Received error from server: {answer.data['message']}")

class SMVP_CANVAS_OT_clearFrames(Operator):
    """Clear all frames of the list"""
    bl_idname = "smvp_canvas.frames_clear"
    bl_label = "Clear Frames"
    bl_description = "Clear all frames of the list"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return bool(context.object.smvp_canvas.frame_list)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = context.object
        if bool(obj.smvp_canvas.frame_list):
            clearFrames(context.scene, obj)
            self.report({'INFO'}, "All items removed")
        else:
            self.report({'INFO'}, "Nothing to remove")
        return{'FINISHED'}


class SMVP_CANVAS_OT_removeDuplicates(Operator):
    """Remove all duplicates"""
    bl_idname = "smvp_canvas.frames_remove_duplicates"
    bl_label = "Remove Duplicates"
    bl_description = "Remove all duplicates"
    bl_options = {'INTERNAL'}

    def find_duplicates(self, context):
        """find all duplicates by name"""
        name_lookup = {}
        for c, i in enumerate(context.object.smvp_canvas.frame_list):
            name_lookup.setdefault(i.name, []).append(c)
        duplicates = set()
        for name, indices in name_lookup.items():
            for i in indices[1:]:
                duplicates.add(i)
        return sorted(list(duplicates))

    @classmethod
    def poll(cls, context):
        return bool(context.object.smvp_canvas.frame_list)

    def execute(self, context):
        obj = context.object
        removed_items = []
        # Reverse the list before removing the items
        for i in self.find_duplicates(context)[::-1]:
            deleteFrameEntry(obj, i)
            removed_items.append(i)
        if removed_items:
            obj.smvp_canvas.frame_list_index = min(obj.smvp_canvas.frame_list_index, len(obj.smvp_canvas.frame_list)-1)
            info = ', '.join(map(str, removed_items))
            self.report({'INFO'}, "Removed indices: %s" % (info))
            update_single_canvas_tex(context.scene, obj)
        else:
            self.report({'INFO'}, "No duplicates")
        return{'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class SMVP_CANVAS_OT_selectFrame(Operator):
    """Jump to Frame in the Timeline"""
    bl_idname = "smvp_canvas.frames_select"
    bl_label = "Jump to Frame"
    bl_description = "Jump to Frame in the Timeline"
    bl_options = {'REGISTER', 'UNDO'}

    jump_to_selected: BoolProperty(
        default=False,
        name="Jump in timeline instead of selecting item at current frame",
        options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return bool(context.object.smvp_canvas.frame_list)

    def execute(self, context):
        scn = context.scene
        obj = context.object

        if self.jump_to_selected:
            idx = obj.smvp_canvas.frame_list_index
            try:
                item = obj.smvp_canvas.frame_list[idx]
            except IndexError:
                self.report({'INFO'}, "Nothing selected in the list")
                return{'CANCELLED'}
            
            frame = int(getKeyframes(obj)[idx][0])
            scn.frame_set(frame)
            self.report({'INFO'}, f"Jumped to frame {frame}")

        else:
            keyframes = getKeyframes(obj)
            # Find first keyframe that is on frame greater than current
            idx = 0
            for x, y in keyframes:
                if x > scn.frame_current:
                    break
                idx += 1
            # Index is previous key (except for first key)
            idx = max(idx-1, 0)
            obj.smvp_canvas.frame_list_index = idx
            self.report({'INFO'}, f"Selected frame {idx} '{obj.smvp_canvas.frame_list[idx].name}'")
        
        return{'FINISHED'}



def update_single_canvas_tex(scene, obj):
    # Get texture to show
    img = getTexture(obj, scene.frame_current)
    
    # If ghosting -> select ghosting frames and apply img + ghosting frames
    if False: # show_ghost:
        frames_before = []
        frames_after = []
        keyframes = getKeyframes(canvas_obj)
        for i in enumerate(keyframes):
            frame_number = keyframes[i][0]
            
        # 
        for idx in frames_before:
            getTextureForIdx(obj, id, display_mode='prev')

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
    mat = bpy.data.materials.new(name=f"canvas_{obj.smvp_canvas.canvas_id:02d}_mat")
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
    item = obj.smvp_canvas.frame_list[index]
    canvas_id = obj.smvp_canvas.canvas_id
    frame_id = item.id

    # Create textures
    tex_name = f"smvp_{canvas_id:02d}-{frame_id:04d}"
    prev_name = f"smvp_prev_{canvas_id:02d}-{frame_id:04d}"
    texture = bpy.data.images.new(tex_name, width=resolution[0], height=resolution[1], float_buffer=True)
    preview = bpy.data.images.new(prev_name, width=resolution[0], height=resolution[1], float_buffer=True)
    
    # Add textures to frame list entry
    item.render_texture = texture.name
    item.preview_texture = preview.name
    

def deleteFrameEntry(obj, index):
    """Deletes the entry at index of the canvas object frame list"""
    item = obj.smvp_canvas.frame_list[index]
    
    # Delete textures
    if item.render_texture in bpy.data.images: bpy.data.images.remove(bpy.data.images[item.render_texture])
    if item.preview_texture in bpy.data.images: bpy.data.images.remove(bpy.data.images[item.preview_texture])
    
    # Remove entry from canvas list and move index
    obj.smvp_canvas.frame_list.remove(index)
    if obj.smvp_canvas.frame_list_index >= index:
        obj.smvp_canvas.frame_list_index -= 1
    
    try:
        # Delete index-th keyframe
        frame_num = getKeyframes(obj)[index][0]
        obj.keyframe_delete('["frame_keys"]', frame=frame_num)
    except:
        pass

def clearFrames(scn, obj):
    for i in reversed(range(len(obj.smvp_canvas.frame_list))):
        deleteFrameEntry(obj, i)
    obj.smvp_canvas.frame_list_index = 0
    update_single_canvas_tex(scn, obj)

def getTexture(canvas_obj, frame):
    canvas = canvas_obj.smvp_canvas
    keyframes = getKeyframes(canvas_obj)
    
    if canvas.display_mode == 'live':
        # No need to look for current key, start live capture with canvas texture
        image_name = canvas.live_texture
        if image_name in bpy.data.images:
            id = client.serviceAddReq(image_name)
            message = ipc.Message(ipc.Command.ReqLive, {'id': id})
            client.sendMessage(message)    
            return bpy.data.images[image_name]
        return None
        
    if len(canvas.frame_list) == 0:
        # No frames in canvas
        return None
    
    # Find frame for current position in timeline
    index = 0 
    for x, y in keyframes:
        if x > frame:
            break
        index += 1
    return getTextureForIdx(canvas_obj, max(0, index-1) % len(canvas.frame_list))
    
def getTextureForIdx(canvas_obj, index, display_mode=None):
    """Returns the texture for the index and display_mode. Uses active display mode if none provided""" 
    canvas = canvas_obj.smvp_canvas
    canvas_frame = canvas.frame_list[index]
    # Get image name for display mode and check if image needs to be requested
    image_name = ""
    command = None
    display_mode = canvas.display_mode if display_mode is None else display_mode
    match display_mode:
        case 'prev': # Preview
            image_name = canvas_frame.preview_texture
            # Request update if image has not been set
            if not canvas_frame.preview_updated:
                command = ipc.Command.ReqPreview
                canvas_frame.preview_updated = True
        case 'bake': # Baked
            image_name = canvas_frame.render_texture
            # Request new image if it hasn't been updated or got replaced
            if not canvas_frame.texture_updated:
                command = ipc.Command.ReqBaked
                canvas_frame.texture_updated = True
        case 'rend': # Render
            image_name = canvas_frame.render_texture
            # Request new image if it hasn't been updated or got replaced TODO?!
            if not canvas_frame.texture_updated:
                command = ipc.Command.ReqRender
                canvas_frame.texture_updated = True
    
    # If image is not valid, create a new one and call function recursively
    if not image_name in bpy.data.images:
        if image_name != "":
            print(f"Error: Image {image_name} missing")
            createFrameTextures(canvas_obj, index, bpy.context.scene.smvp_scene.resolution)
            getTextureForIdx(canvas_obj, index, display_mode)
    
    # If command is set, generate ID for requested image and send request
    if command is not None:
        id = client.serviceAddReq(image_name)
        message = ipc.Message(command, {'id': id})
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

# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    # Override warning OP
    SMVP_CANVAS_OT_overrideConfirm,
    # Frame operators
    SMVP_CANVAS_OT_addFrame,
    SMVP_CANVAS_OT_actions,
    SMVP_CANVAS_OT_capture,
    SMVP_CANVAS_OT_clearFrames,
    SMVP_CANVAS_OT_removeDuplicates,
    SMVP_CANVAS_OT_selectFrame,
    SMVP_CANVAS_OT_ghosting
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


