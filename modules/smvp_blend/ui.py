import bpy
from bpy.types import Panel, Menu

from .client import *
from .domectl import *
from .canvas import *
from .camera import *
from .scene import *

# -------------------------------------------------------------------
# Dome Control
# -------------------------------------------------------------------

class VIEW3D_PT_domectl(Panel): 

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI" #Window  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Stop Motion"  # found in the Sidebar
    bl_label = "Lightdome Controls"  # found at the top of the Panel

    def draw(self, context):
        row = self.layout.row()
        row.operator(WM_OT_smvp_connect.bl_idname, text="(Re-)Connect to service")
        row = self.layout.row()
        row.operator(WM_OT_smvp_launch.bl_idname, text="Launch service")
        row = self.layout.row()
        row.operator(WM_OT_smvp_lightctl.bl_idname, text="Lights on", icon = "OUTLINER_OB_LIGHT").light_state = "TOP"
        row = self.layout.row()
        row.operator(WM_OT_smvp_lightctl.bl_idname, text="Lights off", icon = "OUTLINER_DATA_LIGHT").light_state = "OFF"


# -------------------------------------------------------------------
# Scene, display and capture controls
# -------------------------------------------------------------------

class VIEW3D_PT_stop_motion_vp(Panel): 

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI"  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Stop Motion"  # found in the Sidebar
    bl_label = "Stop Motion VP"  # found at the top of the Panel

    def draw(self, context):
        """define the layout of the panel"""
        layout = self.layout

        row = layout.row()
        row.operator(OBJECT_OT_smvpCanvasAdd.bl_idname, text="Setup Scene", icon ="PLUS")
        row = layout.row()
        row.operator(WM_OT_smvp_viewer.bl_idname, text="Toggle Live View", icon = "SCENE")
        row = layout.row()
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_ANIMATION", text="Capture Full Sequence")
        row = layout.row()
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_STILL", text="Capture Baked Lights").baked = True


class VIEW3D_PT_onionskin(Panel):

    bl_space_type = "VIEW_3D" 
    bl_region_type = "UI"  

    bl_category = "Stop Motion" 
    bl_label = "Show Ghosting" 

    bl_parent_id = "VIEW3D_PT_stop_motion_vp" # makes it into a subpanel
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self,context):
        # use layout property to display a checkbox, can be anything
        self.layout.prop(context.scene.render, "use_border", text="", icon = "GHOST_ENABLED")
 
    def draw(self, context):        
        self.layout.label(text="Display Ghostframes", icon='NONE')
        row = self.layout.row()
        row.prop(context.scene, "frame_start", text = "pre")
        row.prop(context.scene, "frame_end", text = "post") 
        row = self.layout.row()
        row.prop(context.scene, "frame_start", text= "Opacity")

# TODO find a way to disable subpanel when unchecked 
# https://blender.stackexchange.com/questions/212075/how-to-enable-or-disable-panels-with-the-click-of-a-button


 
class VIEW3D_PT_algorithm(bpy.types.Panel):
    bl_label = "Choose Algorithm"
    bl_idname = "VIEW3D_PT_select_algorithm"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Stop Motion"
    bl_parent_id = "VIEW3D_PT_stop_motion_vp"
    bl_options = {"DEFAULT_CLOSED"}
 
      
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        algs = scene.smvp_algorithms
        wm = context.window_manager
       
        layout.prop(algs, "algs_dropdown_items")
        layout.operator("mesh.primitive_monkey_add", text="Apply")
        #layout.prop(wm, 'toggle_render_algs', text=label, toggle=True)
  

class VIEW3D_OT_render_algorithms(Operator):
    """ Render Canvases with chosen Algorithm"""
    bl_idname = "algs.render"
    bl_label = "render_algorithms"

    def modal(self, context, event):
        scene = context.scene
        algs = scene.smvp_algorithms
           
        if context.window_manager.toggle_render_algs:
            if algs.algs_dropdown_items == 'id00': #default
                bpy.context.space_data.shading.type = "SOLID"

            if algs.algs_dropdown_items == 'id1':
                bpy.context.space_data.shading.type = "WIREFRAME"

            return {'FINISHED'} 
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class SMVP_CANVAS_PT_canvasProps(Panel):
    """Adds a Canvas Properties Panel to the N Bar Interface"""
    bl_idname = 'OBJECT_PT_canvasprops'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Active Canvas"
    bl_category = "Stop Motion"
    bl_parent_id = "VIEW3D_PT_stop_motion_vp"

      
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        obj = context.object
        active = scn.smvp_scene.active_canvas


        row = layout.row(align=True)
        if not active in context.scene.objects:
            active = "No active Canvas"
            row.label(text = "", icon = "ERROR") 
        row.label(text = active) 

        if obj.smvp_canvas.is_canvas:
                  
            if active != obj.name:
                #only draw icon to refresh, if selected isn't active
                row.operator("smvp_canvas.activate_selected", text = "",  icon = "FILE_REFRESH")

    
        
            



# -------------------------------------------------------------------
# Canvas UI
# -------------------------------------------------------------------

class SMVP_CANVAS_UL_items(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.3)
        split.label(text="Index: %d" % (index))
        #custom_icon = "OUTLINER_OB_%s" % item.obj_type
        #split.prop(item, "name", text="", emboss=False, translate=False, icon=custom_icon)
        split.label(text=item.name)#, icon=custom_icon) # avoids renaming the item by accident

    def invoke(self, context, event):
        pass   

class SMVP_CANVAS_PT_frameList(Panel):
    """Adds a frame list panel to the object properties"""
    bl_idname = 'OBJECT_PT_frames_panel'
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_label = "Frame List"
    bl_context = "object"
    
    @classmethod
    def poll(cls, context):
        """Only draw panel for canvas objects"""
        return context.object.smvp_canvas.is_canvas
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        obj = context.object

        rows = 2
        row = layout.row()
        row.template_list("SMVP_CANVAS_UL_items", "", obj.smvp_canvas, "frame_list", obj.smvp_canvas, "frame_list_index", rows=rows)

        col = row.column(align=True)
        col.operator(SMVP_CANVAS_OT_addFrame.bl_idname, icon='ADD', text="")
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='REMOVE', text="").action = 'REMOVE'
        col.separator()
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='TRIA_UP', text="").action = 'UP'
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='TRIA_DOWN', text="").action = 'DOWN'

        row = layout.row()
        col = row.column(align=True)
        row = col.row(align=True)
        row.operator(WM_OT_smvp_viewer.bl_idname, text="Camera Live View", icon = "SCENE")
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_ANIMATION", text="Capture Full Sequence")
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_STILL", text="Capture Baked Lights").baked = True
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_selectFrame.bl_idname, icon="LAYER_ACTIVE", text="Select current frame")
        row.operator(SMVP_CANVAS_OT_selectFrame.bl_idname, icon="ARROW_LEFTRIGHT", text="Jump to selected").jump_to_selected = True
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_removeDuplicates.bl_idname, icon="TRASH")
        row.operator(SMVP_CANVAS_OT_clearFrames.bl_idname, icon="PANEL_CLOSE")



# -------------------------------------------------------------------
# Camera UI
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Add Menu Entry
# -------------------------------------------------------------------

class OBJECT_MT_smvp_submenu(Menu):
    bl_idname = "OBJECT_MT_smvp_submenu"
    bl_label = "Stop Motion Virtual Production"

    def draw(self, context):
        layout = self.layout
        layout.operator(OBJECT_OT_smvpCanvasAdd.bl_idname, text="Canvas", icon="IMAGE_PLANE")
        layout.operator(SMVP_CAMERA_OT_addLinked.bl_idname, text="Linked Camera", icon="VIEW_CAMERA")
    
        
def smvp_objects_menu(self, context):
    self.layout.separator()
    self.layout.menu(OBJECT_MT_smvp_submenu.bl_idname, text="SMVP", icon="GHOST_DISABLED")



# -------------------------------------------------------------------
# un/register
# -------------------------------------------------------------------

classes =(
    # Dome Control
    VIEW3D_PT_domectl,
    
    # Stop Motion VP
    VIEW3D_PT_stop_motion_vp,
    VIEW3D_PT_onionskin,
        # Render Algorithms
    VIEW3D_PT_algorithm, 
    VIEW3D_OT_render_algorithms, 
     
    # Canvas UI
    SMVP_CANVAS_UL_items,
    SMVP_CANVAS_PT_frameList,
    SMVP_CANVAS_PT_canvasProps,

    # Menus
    OBJECT_MT_smvp_submenu,

)

def register():
    # Register classes
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add menus
    bpy.types.VIEW3D_MT_add.append(smvp_objects_menu)
    
   

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

   # Remove menus
    bpy.types.VIEW3D_MT_add.remove(smvp_objects_menu)
    

