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

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        # Call operator again with override set
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
            createFrameTextures(obj, new_index, (1920, 1080))
            
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



class SMVP_CANVAS_OT_capture(Operator):
    """Capture frame data for rendering or with baked lighting"""
    bl_idname = "smvp_canvas.capture"
    bl_label = "Capture"
    bl_description = "Capture frame data for rendering or with baked lighting"
    bl_options = {'REGISTER', 'UNDO'}
    
    baked: BoolProperty(name="Capture with baked HDRI", default=False)
    frame: IntProperty(name="Frame number for the captured frame (-1 for current frame)", default=-1) # Or float?

    def execute(self, context):
        obj = context.object
        tex = obj.smvp_canvas.frame_list[0].preview_texture
        
        id = client.serviceAddReq(tex)
        #message = ipc.Message(ipc.Command.PreviewLive, {'id': id})
        #message = ipc.Message(ipc.Command.PreviewHdri, {'id': id})
        # Send capture message
        message = None
        if self.baked:
            message = ipc.Message(ipc.Command.CaptureBaked, {'id': id})
        else:
            message = ipc.Message(ipc.Command.CaptureLights, {'id': id})
        client.sendMessage(message)
        
        return{'FINISHED'}



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
            for i in reversed(range(len(obj.smvp_canvas.frame_list))):
                deleteFrameEntry(obj, i)
            obj.smvp_canvas.frame_list_index = 0
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
        idx = obj.smvp_canvas.frame_list_index

        try:
            item = obj.smvp_canvas.frame_list[idx]
        except IndexError:
            self.report({'INFO'}, "Nothing selected in the list")
            return{'CANCELLED'}

        obj_error = False
        bpy.ops.object.select_all(action='DESELECT')
        if not self.select_all:
            obj = scn.objects.get(obj.smvp_canvas.frame_list[idx].name, None)
            if not obj: 
                obj_error = True
            else:
                obj.select_set(True)
                info = '"%s" selected in Viewport' % (obj.name)
        else:
            selected_items = []
            unique_objs = set([i.name for i in obj.smvp_canvas.frame_list])
            for i in unique_objs:
                obj = scn.objects.get(i, None)
                if obj:
                    obj.select_set(True)
                    selected_items.append(obj.name)

            if not selected_items: 
                obj_error = True
            else:
                missing_items = unique_objs.difference(selected_items)
                if not missing_items:
                    info = '"%s" selected in Viewport' \
                        % (', '.join(map(str, selected_items)))
                else:
                    info = 'Missing items: "%s"' \
                        % (', '.join(map(str, missing_items)))
        if obj_error: 
            info = "Nothing to select, object removed from scene"
        self.report({'INFO'}, info)    
        return{'FINISHED'}


# -------------------------------------------------------------------
#   Side-Panel (3D-View) Operators
# -------------------------------------------------------------------
class OBJECT_OT_smvp_canvas_add(bpy.types.Operator):
    """Creates an canvas object"""

    bl_idname = "object.smvp_create_canvas"
    bl_label = "Creates an canvas object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Add primitive
        bpy.ops.mesh.primitive_plane_add(rotation=(math.pi/2, 0, 0), size=2)
        canvas = bpy.context.object
        # Properties
        canvas.name = "Canvas"
        canvas.scale[0] = 16/9
        canvas.smvp_canvas.is_canvas = True
        canvas['exposure'] = 1.0
        #canvas['exposure_preview'] = 1.0
        canvas['frame_keys'] = True
        
        # Set ID and increment
        canvas.smvp_canvas.canvas_id = context.scene.smvp_scene.canvas_ids
        context.scene.smvp_scene.canvas_ids += 1
        
        # Set material, create slot and assign
        mat = createCanvasMat(canvas)
        canvas.data.materials.append(mat)
        # Settings TODO only for EEVEE?
        mat.blend_method = 'HASHED'
        mat.shadow_method = 'HASHED'
        
        # Set active canvas object if not set
        if context.scene.smvp_scene.active_canvas == "":
            context.scene.smvp_scene.active_canvas = canvas.name
        
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
            update_single_canvas_tex(scene, obj)
            
                
def update_single_canvas_tex(scene, obj):
    try:
        idx = obj.smvp_canvas.frame_list_index # TODO
        item = obj.smvp_canvas.frame_list[idx]
    except:
        pass
    else:
        # Apply texture
        img = getTexture(obj, scene.frame_current)
        obj.active_material.node_tree.nodes["ImageTexture"].image = img



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
    item.rendered_texture = texture.name
    item.preview_texture = preview.name
    

def deleteFrameEntry(obj, index):
    """Deletes the entry at index of the canvas object frame list"""
    item = obj.smvp_canvas.frame_list[index]
    
    # Delete textures
    if item.rendered_texture in bpy.data.images: bpy.data.images.remove(bpy.data.images[item.rendered_texture])
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

def getTexture(canvas_obj, frame):
    canvas = canvas_obj.smvp_canvas
    keyframes = getKeyframes(canvas_obj)
    index = 0 
    for x, y in keyframes:
        if x > frame:
            break
        index += 1
        
    canvas_frame = canvas.frame_list[max(0, index-1) % len(canvas.frame_list)]
    image_name = ""
    
    if canvas.display_preview:
        # Check if image exists, create new one if missing
        image_name = canvas_frame.preview_texture
        if not image_name in bpy.data.images:
            print(f"Error: Image {image_name} missing")
            return None # createFrameTextures(canvas_obj, index, (1920, 1080)) # TODO
        
        if not canvas_frame.preview_updated:
            # Request preview texture
            id = client.serviceAddReq(image_name)
            message = ipc.Message(ipc.Command.Preview, {'id': id})
            client.sendMessage(message)
            
            # Frame texture was updated
            canvas_frame.preview_updated = True
        
    else:
        # Rendered frame
        image_name = canvas_frame.rendered_texture
        if not image_name in bpy.data.images:
            print(f"Error: Image {image_name} missing")
            return None # createFrameTextures(canvas_obj, index, (1920, 1080)) # TODO
        
        if not canvas_frame.updated:
            # Request rendered texture
            id = client.serviceAddReq(image_name)
            message = ipc.Message(ipc.Command.Preview, {'id': id}) # TODO render, nicht preview!!
            client.sendMessage(message)
            
            # Frame texture was updated
            canvas_frame.updated = True
            
    
    # Return texture (or none if it got deleted)
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
    
    # Canvas object operators
    OBJECT_OT_smvp_canvas_add,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    # Event handlers
    bpy.app.handlers.frame_change_pre.append(update_canvas_textures)
    bpy.app.handlers

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


