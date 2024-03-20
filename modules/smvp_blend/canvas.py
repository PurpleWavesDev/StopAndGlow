import math

import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from . import properties as props
#from . import client

# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------

## Frame UIList Operators
class SMVP_CANVAS_OT_actions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "smvp_canvas.frames_action"
    bl_label = "Frame List Actions"
    bl_description = "Move frame items up and down, add and remove"
    bl_options = {'REGISTER'}

    action: EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", "")))

    def invoke(self, context, event):
        scn = context.scene
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
                info = 'Item "%s" moved to position %d' % (item.name, obj.smvp_canvas.frame_list_index + 1)
                self.report({'INFO'}, info)

            elif self.action == 'UP' and idx >= 1:
                item_prev = obj.smvp_canvas.frame_list[idx-1].name
                obj.smvp_canvas.frame_list.move(idx, idx-1)
                obj.smvp_canvas.frame_list_index -= 1
                info = 'Item "%s" moved to position %d' % (item.name, obj.smvp_canvas.frame_list_index + 1)
                self.report({'INFO'}, info)

            elif self.action == 'REMOVE':
                info = 'Item "%s" removed from list' % (obj.smvp_canvas.frame_list[idx].name)
                obj.smvp_canvas.frame_list_index -= 1
                obj.smvp_canvas.frame_list.remove(idx)
                self.report({'INFO'}, info)

        if self.action == 'ADD':
            if context.object:
                item = obj.smvp_canvas.frame_list.add()
                item.name = context.object.name
                item.obj_type = context.object.type
                item.obj_id = len(obj.smvp_canvas.frame_list)
                obj.smvp_canvas.frame_list_index = len(obj.smvp_canvas.frame_list)-1
                info = '"%s" added to list' % (item.name)
                self.report({'INFO'}, info)
            else:
                self.report({'INFO'}, "Nothing selected in the Viewport")
        return {"FINISHED"}


class SMVP_CANVAS_OT_printFrames(Operator):
    """Print all frames and their properties to the console, for debugging purposes"""
    bl_idname = "smvp_canvas.frames_print"
    bl_label = "Print Frames to Console"
    bl_description = "Print all frames and their properties to the console"
    bl_options = {'REGISTER', 'UNDO'}

    reverse_order: BoolProperty(
        default=False,
        name="Reverse Order")

    @classmethod
    def poll(cls, context):
        return bool(context.object.smvp_canvas.frame_list)

    def execute(self, context):
        scn = context.scene
        if self.reverse_order:
            for i in range(obj.smvp_canvas.frame_list_index, -1, -1):        
                item = obj.smvp_canvas.frame_list[i]
                print ("Name:", item.name,"-",item.obj_type,item.obj_id)
        else:
            for item in obj.smvp_canvas.frame_list:
                print ("Name:", item.name,"-",item.obj_type,item.obj_id)
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
        if bool(context.object.smvp_canvas.frame_list):
            context.object.smvp_canvas.frame_list.clear()
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
        scn = context.scene
        removed_items = []
        # Reverse the list before removing the items
        for i in self.find_duplicates(context)[::-1]:
            obj.smvp_canvas.frame_list.remove(i)
            removed_items.append(i)
        if removed_items:
            obj.smvp_canvas.frame_list_index = len(obj.smvp_canvas.frame_list)-1
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


## N-Panel Operators
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



# -------------------------------------------------------------------
#   Event handlers
# -------------------------------------------------------------------
def update_canvas_frame(scene):
    #bpy.data.materials["Video"].node_tree.nodes["texture"].inputs[1].default_value = frame_numscene.frame_current
    for obj in bpy.data.objects:
        if obj.smvp_canvas.is_canvas:
            # Canvas found! Iterate over available frames
            for key, val in obj.smvp_canvas.frames.items():
                obj_key = "frame_"+str(key)
                key_num = -1
                # Create new property if it doesn't exist and set key
                if not obj_key in obj.keys():
                    obj[obj_key] = True
                    obj.keyframe_insert(data_path=obj_key, frame=key)
                    obj.smvp_canvas.keyframes[key] = key
                # Otherwise find keys
                else:
                    for fc in obj.animation_data.action.fcurves:
                        if fc.data_path == obj_key:
                            for key_val in fc.keyframe_points:
                                #print('frame:',key_val.co[0],'value:',key_val.co[1])
                                obj.smvp_canvas.keyframes[key_val.co[0]] = key
            # Sort keyframes
            obj.smvp_canvas.keyframes = dict(sorted(obj.smvp_canvas.keyframes.items()))
    
    # Update offsets
    update_canvas_frame_offset(scene)

def update_canvas_frame_offset(scene):
    for obj in bpy.data.objects:
        if obj.smvp_canvas.is_canvas:
            # Assign current frame offset
            obj.smvp_canvas.offset = scene.frame_current


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    # Frame operators
    SMVP_CANVAS_OT_actions,
    SMVP_CANVAS_OT_printFrames,
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
    #bpy.app.handlers.frame_change_pre.append(update_canvas_frame)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


