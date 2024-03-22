import math
import os
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from smvp_ipc import *

from . import properties as props
from . import client

DEFAULT_RESOULTION = (1920, 1080)

# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------

## Frame UIList Operators
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

    def invoke(self, context, event):
        # Add new sequence as frame entry
        # Open browser, will write selected path into our directory property
        context.window_manager.fileselect_add(self)
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}

    def execute(self, context):
        obj = context.object
        idx = obj.smvp_canvas.frame_list_index
        
        # Check if directory is a valid folder
        if os.path.isdir(self.directory):
            # TODO: Index and resolution!
            createFrameEntry(obj, self.directory, (1920, 1080), -1)
            # Force redraw
            context.area.tag_redraw()
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

        return {"FINISHED"}

    #def execute(self, context):
    #    obj = context.object
    #    idx = obj.smvp_canvas.frame_list_index
    #                
    #    return {"FINISHED"}


class SMVP_CANVAS_OT_printFrames(Operator):
    """Print all frames and their properties to the console, for debugging purposes"""
    bl_idname = "smvp_canvas.frames_print"
    bl_label = "Print Frames to Console"
    bl_description = "Print all frames and their properties to the console"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        tex = obj.smvp_canvas.frame_list[0].preview_texture
        
        id = client.serviceAddReq(bpy.data.images[tex])
        #message = Message(Command.PreviewLive, {'id': id})
        message = Message(Command.PreviewHdri, {'id': id})
        client.sendMessage(message)
        return{'FINISHED'}
    
class SMVP_CANVAS_OT_printFrames_cpy(Operator):
    """Print all frames and their properties to the console, for debugging purposes"""
    bl_idname = "smvp_canvas.frames_print_cpy"
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
        obj = context.object
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
        obj = context.object
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
        # Add primitive
        bpy.ops.mesh.primitive_plane_add(rotation=(math.pi/2, 0, 0), size=2)
        canvas = bpy.context.object
        # Properties
        canvas.name = "Canvas"
        canvas.scale[0] = 16/9
        canvas.smvp_canvas.is_canvas = True
        canvas['exposure'] = 1.0
        
        # Set material
        mat = createCanvasMat(canvas)
        # Create slot and assign
        canvas.data.materials.append(mat)
        # Settings TODO only for EEVEE?
        mat.blend_method = 'HASHED'
        mat.shadow_method = 'HASHED'
        
        return {"FINISHED"}
    
    def invoke(self, context, event):
        return self.execute(context)



# -------------------------------------------------------------------
#   Event handlers
# -------------------------------------------------------------------
def update_canvases_texture(scene):
    #bpy.data.materials["Video"].node_tree.nodes["texture"].inputs[1].default_value = frame_numscene.frame_current
    for obj in bpy.data.objects:
        if obj.smvp_canvas.is_canvas:
            pass
            # Canvas found! Find current frame
            
            # Apply texture



# -------------------------------------------------------------------
#   Helpers
# -------------------------------------------------------------------
def createCanvasMat(obj):
    # Create empty material
    mat = bpy.data.materials.new(name=obj.name+"_mat")
    mat.use_nodes = True
    mat.node_tree.nodes.remove(mat.node_tree.nodes['Principled BSDF'])

    # Create mix shader node and link with output
    mix = mat.node_tree.nodes.new('ShaderNodeMixShader')
    matout = mat.node_tree.nodes.get('Material Output')
    mat.node_tree.links.new(matout.inputs[0], mix.outputs[0])
    
    # Create transparency shader and link with mix shader
    trans = mat.node_tree.nodes.new('ShaderNodeBsdfTransparent')
    mat.node_tree.links.new(mix.inputs[1], trans.outputs[0])
    
    # Create emission shader and value node and link with mix shader
    emission = mat.node_tree.nodes.new('ShaderNodeEmission')
    exposure = mat.node_tree.nodes.new('ShaderNodeValue')
    mat.node_tree.links.new(mix.inputs[2], emission.outputs[0])
    mat.node_tree.links.new(emission.inputs[1], exposure.outputs[0])
    
    # Create image texture node and link with HSV
    img = mat.node_tree.nodes.new('ShaderNodeTexImage')
    mat.node_tree.links.new(emission.inputs[0], img.outputs[0])
    # Create color ramp to connect image alpha (depth mask?) with mix node
    ramp = mat.node_tree.nodes.new('ShaderNodeValToRGB') # ShaderNodeMapRange
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

def createFrameEntry(obj, path, resolution, index=-1):
    item = obj.smvp_canvas.frame_list.add()
    item.seq_path = os.path.normpath(path)
    item.name = os.path.basename(item.seq_path)
    
    # Create textures
    tex_name = "smvp_"+item.name
    texture = bpy.data.images.new(tex_name, width=resolution[0], height=resolution[1], float_buffer=True)
    preview = bpy.data.images.new(tex_name+'_prev', width=resolution[0], height=resolution[1], float_buffer=True)
    # Add to frame list entry
    item.rendered_texture = texture.name
    item.preview_texture = preview.name
    
    if index != -1:
        # Move frame to index TODO
        pass

def getTexture(canvas_obj, frame):
    canvas = canvas_obj.smvp_canvas
    canvas_frame = canvas.frame_list[frame % len(canvas.frame_list)]
    image_name = ""
    
    if canvas.display_preview:
        if not canvas_frame.preview_updated:
            # Request preview texture
            
            # Frame texture was updated
            canvas_frame.preview_updated = True
        
        image_name = canvas_frame.preview_texture
    
    else:
        # Rendered frame
        if not canvas_frame.updated:
            # Request rendered texture
            
            # Frame texture was updated
            canvas_frame.updated = True
            
        image_name = canvas_frame.rendered_texture
    
    if image_name in bpy.data.images:
        return bpy.data.images[image_name]
    elif 'smvp_empty' in bpy.data.images:
        return bpy.data.images['smvp_empty']
    else:
        return bpy.data.images.new('smvp_empty', width=DEFAULT_RESOULTION[0], height=DEFAULT_RESOULTION[1])


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    # Frame operators
    SMVP_CANVAS_OT_addFrame,
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
    bpy.app.handlers.frame_change_pre.append(update_canvases_texture)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


