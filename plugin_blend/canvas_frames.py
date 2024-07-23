import math
import os
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList
import numpy as np

import sng_ipc as ipc

from .canvas import *
from . import properties as props
from . import client


# -------------------------------------------------------------------
#   Frame UI List Operators
# -------------------------------------------------------------------

class SNG_CANVAS_OT_overrideConfirm(Operator):
    """Override current frame?"""
    bl_idname = "sng_canvas.override_confirm"
    bl_label = "Override current frame?"
    bl_options = {'REGISTER', 'INTERNAL'}

    capture: BoolProperty(name="Call capture instead of add", default=False)
    use_active: BoolProperty(name="Use active canvas", default=False)
    
    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        # Call operator again with override set
        if self.capture:
            bpy.ops.sng_canvas.capture('INVOKE_DEFAULT', override=True, use_active=self.use_active)
        else:
            bpy.ops.sng_canvas.frame_add('INVOKE_DEFAULT', override=True)
        return {'FINISHED'}
    
class SNG_CANVAS_OT_addFrame(Operator):
    """Add new frame from sequence folder"""
    bl_idname = "sng_canvas.frame_add"
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
    use_active: BoolProperty(
        default=False,
        name="Use default canvas",
    )

    def invoke(self, context, event):
        # Add new sequence as frame entry
        scn = context.scene
        obj = scn.sl_canvas if self.use_active else context.object
        
        if not self.override:
            # Check if there is a keyframe already that would be overwritten
            keyframes = getKeyframes(obj)
            for x, y in keyframes:
                if x == scn.frame_current:
                    bpy.ops.sng_canvas.override_confirm('INVOKE_DEFAULT')
                    return {'RUNNING_MODAL'}

        # Open browser, will write selected path into our directory property
        context.window_manager.fileselect_add(self)
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}

    def execute(self, context):
        scn = context.scene
        obj = scn.sl_canvas if self.use_active else context.object
        canvas = obj.sng_canvas
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
            createFrameTextures(obj, new_index, scn.sng_scene.resolution)
            
            # Insert keyframe
            obj.keyframe_insert(data_path='["frame_keys"]')
            
            # Send load command
            message = ipc.Message(ipc.Command.LoadFootage, {'path': self.directory})
            answer = client.sendMessage(message)
            # Check answer, cancel if received an error
            if answer is None or answer.command != ipc.Command.CommandOkay:
                self.report({'WARNING'}, "Can't add frame")
                return {"CANCELLED"}
            
            context.area.tag_redraw()
            
            # Update texture
            updateCanvas(scn, obj)
            return {"FINISHED"}
            
        else:
            self.report({'WARNING'}, "Not a valid folder: " + self.directory)
            return {"CANCELLED"}

      


class SNG_CANVAS_OT_actions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "sng_canvas.frame_action"
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
        return len(context.object.sng_canvas.frame_list) > 0
    
    def invoke(self, context, event):
        obj = context.object
        idx = obj.sng_canvas.frame_list_index
        
        try:
            item = obj.sng_canvas.frame_list[idx]
        except IndexError:
            pass
        else:
            if self.action == 'DOWN' and idx < len(obj.sng_canvas.frame_list) - 1:
                item_next = obj.sng_canvas.frame_list[idx+1].name
                obj.sng_canvas.frame_list.move(idx, idx+1)
                obj.sng_canvas.frame_list_index += 1
                info = 'Frame "%s" moved to position %d' % (item.name, obj.sng_canvas.frame_list_index + 1)
                self.report({'INFO'}, info)

            elif self.action == 'UP' and idx >= 1:
                item_prev = obj.sng_canvas.frame_list[idx-1].name
                obj.sng_canvas.frame_list.move(idx, idx-1)
                obj.sng_canvas.frame_list_index -= 1
                info = 'Frame "%s" moved to position %d' % (item.name, obj.sng_canvas.frame_list_index + 1)
                self.report({'INFO'}, info)

            elif self.action == 'REMOVE':
                info = 'Frame "%s" removed from list' % (obj.sng_canvas.frame_list[idx].name)
                deleteFrameEntry(obj, idx)
                if obj.sng_canvas.frame_list_index >= idx:
                    obj.sng_canvas.frame_list_index -= 1
                self.report({'INFO'}, info)
            
        updateCanvas(context.scene, obj)
        return {"RUNNING_MODAL"}


class SNG_CANVAS_OT_capture(Operator):
    """Capture frame data for rendering or with baked lighting"""
    bl_idname = "sng_canvas.capture"
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
    use_active: BoolProperty(
        default=False,
        name="Use default canvas",
    )

    def invoke(self, context, event):
        # Add new sequence as frame entry
        scn = context.scene
        obj = scn.sl_canvas if self.use_active else context.object
        
        if not self.override:
            # Check if there is a keyframe already that would be overwritten
            keyframes = getKeyframes(obj)
            for x, y in keyframes:
                if x == scn.frame_current:
                    bpy.ops.sng_canvas.override_confirm('INVOKE_DEFAULT', capture=True)
                    return {'RUNNING_MODAL'}

        # Execute capture command
        return self.execute(context)
    
    def execute(self, context):
        # Send capture message
        message = None
        if self.baked:
            message = ipc.Message(ipc.Command.CaptureBaked, {'name': self.name})
        else:
            message = ipc.Message(ipc.Command.CaptureLights, {'name': self.name})
        answer = client.sendMessage(message)
        
        if answer.command == ipc.Command.CommandProcessing:
            # Add frame to list
            bpy.ops.sng_canvas.frame_add(directory=answer.data['path'], override=True, use_active=self.use_active)
            return {'FINISHED'}

        self.report({'WARNING'}, f"Received error from server: {answer.data['message']}")
        return {'CANCELLED'}

class SNG_CANVAS_OT_clearFrames(Operator):
    """Clear all frames of the list"""
    bl_idname = "sng_canvas.frames_clear"
    bl_label = "Clear Frames"
    bl_description = "Clear all frames of the list"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return bool(context.object.sng_canvas.frame_list)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = context.object
        if bool(obj.sng_canvas.frame_list):
            clearFrames(context.scene, obj)
            self.report({'INFO'}, "All items removed")
        else:
            self.report({'INFO'}, "Nothing to remove")
        return{'FINISHED'}


class SNG_CANVAS_OT_removeDuplicates(Operator):
    """Remove all duplicates"""
    bl_idname = "sng_canvas.frames_remove_duplicates"
    bl_label = "Remove Duplicates"
    bl_description = "Remove all duplicates"
    bl_options = {'INTERNAL'}

    def find_duplicates(self, context):
        """find all duplicates by name"""
        name_lookup = {}
        for c, i in enumerate(context.object.sng_canvas.frame_list):
            name_lookup.setdefault(i.name, []).append(c)
        duplicates = set()
        for name, indices in name_lookup.items():
            for i in indices[1:]:
                duplicates.add(i)
        return sorted(list(duplicates))

    @classmethod
    def poll(cls, context):
        return bool(context.object.sng_canvas.frame_list)

    def execute(self, context):
        obj = context.object
        removed_items = []
        # Reverse the list before removing the items
        for i in self.find_duplicates(context)[::-1]:
            deleteFrameEntry(obj, i)
            removed_items.append(i)
        if removed_items:
            obj.sng_canvas.frame_list_index = min(obj.sng_canvas.frame_list_index, len(obj.sng_canvas.frame_list)-1)
            info = ', '.join(map(str, removed_items))
            self.report({'INFO'}, "Removed indices: %s" % (info))
            updateCanvas(context.scene, obj)
        else:
            self.report({'INFO'}, "No duplicates")
        return{'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class SNG_CANVAS_OT_selectFrame(Operator):
    """Jump to Frame in the Timeline"""
    bl_idname = "sng_canvas.frames_select"
    bl_label = "Jump to Frame"
    bl_description = "Jump to Frame in the Timeline"
    bl_options = {'REGISTER', 'UNDO'}

    jump_to_selected: BoolProperty(
        default=False,
        name="Jump in timeline instead of selecting item at current frame",
        options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return bool(context.object.sng_canvas.frame_list)

    def execute(self, context):
        scn = context.scene
        obj = context.object

        if self.jump_to_selected:
            idx = obj.sng_canvas.frame_list_index
            try:
                item = obj.sng_canvas.frame_list[idx]
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
            obj.sng_canvas.frame_list_index = idx
            self.report({'INFO'}, f"Selected frame {idx} '{obj.sng_canvas.frame_list[idx].name}'")
        
        return{'FINISHED'}
    

# -------------------------------------------------------------------
#   Frames & Keyframes Helpers
# -------------------------------------------------------------------
def deleteFrameEntry(obj, index):
    """Deletes the entry at index of the canvas object frame list"""
    item = obj.sng_canvas.frame_list[index]
    
    # Delete textures
    if item.render_texture in bpy.data.images: bpy.data.images.remove(bpy.data.images[item.render_texture])
    if item.preview_texture in bpy.data.images: bpy.data.images.remove(bpy.data.images[item.preview_texture])
    
    # Remove entry from canvas list and move index
    obj.sng_canvas.frame_list.remove(index)
    if obj.sng_canvas.frame_list_index >= index:
        obj.sng_canvas.frame_list_index -= 1
    
    try:
        # Delete index-th keyframe
        frame_num = getKeyframes(obj)[index][0]
        obj.keyframe_delete('["frame_keys"]', frame=frame_num)
    except:
        pass


def clearFrames(scn, obj):
    for i in reversed(range(len(obj.sng_canvas.frame_list))):
        deleteFrameEntry(obj, i)
    obj.sng_canvas.frame_list_index = 0
    updateCanvas(scn, obj)


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    # Override warning OP
    SNG_CANVAS_OT_overrideConfirm,
    # Frame operators
    SNG_CANVAS_OT_addFrame,
    SNG_CANVAS_OT_actions,
    SNG_CANVAS_OT_capture,
    SNG_CANVAS_OT_clearFrames,
    SNG_CANVAS_OT_removeDuplicates,
    SNG_CANVAS_OT_selectFrame,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


