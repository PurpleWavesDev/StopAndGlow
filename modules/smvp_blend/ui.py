import bpy
from bpy.types import Panel, Menu

from .client import *
from .domectl import *
from .canvas import *
from .camera import *
from .scene import *


# -------------------------------------------------------------------
# Scene Panel: Displays and sets active canvas, setup scene
# -------------------------------------------------------------------

class VIEW3D_PT_sl_scene(Panel): 

    bl_space_type = "VIEW_3D" 
    bl_region_type = "UI" 

    bl_category = "Stop Lighting" 
    bl_label = "Scene" 
    bl_idname = "VIEW3D_PT_sl_scene" 
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        scn = context.scene
        canvas = scn.sl_canvas
        
        # Active canvas display
        icon = "NONE"
        if canvas is None:
            icon="ERROR"
        split = layout.split(factor=0.5)
        split.label(text ="Active Canvas")
        split.prop_search(scn, "sl_canvas", scn, "objects", text="", icon=icon, )
        # Assign current
        if obj is not None and obj.smvp_canvas.is_canvas:
            # only draw icon to refresh, if selected isn't active
            if canvas != obj:
                row = self.layout.row()
                row.operator("smvp_canvas.set_active", text = "Assign current",  icon = "FILE_REFRESH")

        # Setup Scene OP
        layout.separator()
        split = layout.split(factor=0.5)
        split.label(text="Scene Setup")
        split.operator(OBJECT_OT_smvpCanvasAdd.bl_idname, text="New", icon ="PLUS")


# -------------------------------------------------------------------
# Capture & Display: Capture, Display Modes, Render Algorithms and Ghosting
# -------------------------------------------------------------------        
            
class VIEW3D_PT_renderctl(bpy.types.Panel):
    """Choose how to display the Canvases in Scene"""
    bl_label = "Display"
    bl_idname = "VIEW3D_PT_render_ctls"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Stop Lighting"
    #bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        return context.scene.sl_canvas is not None
 
      
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        algs = scene.smvp_algorithms
        ghostIcon = ""
        obj = context.scene.sl_canvas
      
        row = layout.row()
        row.label(text= "Render Modes")
        row.prop(obj.smvp_canvas,'display_mode',expand = True)

        row = self.layout.row()
        row.operator(SMVP_CANVAS_OT_updateScene.bl_idname, icon="RECOVER_LAST", text="Update")
        row = self.layout.row()
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_STILL", text="Capture")

        header, panel = layout.panel("algs_panel_id", default_closed=False)
        header.label(text="Algorithms")
        if panel:
            panel.prop(algs, "algs_dropdown_items", expand = False)
            panel.operator(SMVP_CANVAS_OT_applyRenderAlgorithm.bl_idname)  
        
        ghostIcon=  "GHOST_ENABLED" if obj.smvp_ghost.show_ghost else "GHOST_DISABLED"
        ghostLabel= "Hide Ghostframes" if obj.smvp_ghost.show_ghost else "Display Ghostframes"
          
        header, panel = layout.panel("onion_skinning", default_closed=False)
        header.operator(SMVP_CANVAS_OT_setGhostMode.bl_idname, text= ghostLabel, icon=ghostIcon)
       

        if panel:
            row=panel.row()
            row.label(text="Previous")
            row.prop(obj.smvp_ghost, "previous_frames", text = "")

            row= panel.row()
            row.label(text="Post")
            row.prop(obj.smvp_ghost, "following_frames", text="") 

            panel.prop(obj.smvp_ghost, "opacity", text= "Opacity", slider = True)
            
  
# -------------------------------------------------------------------
# Dome Control
# -------------------------------------------------------------------

class VIEW3D_PT_domectl(Panel): 

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI" #Window  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Stop Lighting"  # found in the Sidebar
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
# Canvas UI
# -------------------------------------------------------------------

class SL_CANVAS_UL_items(UIList):
    bl_idname = 'SL_CANVAS_UL_items'
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.3)
        split.label(text="Index: %d" % (index))
        #custom_icon = "OUTLINER_OB_%s" % item.obj_type
        #split.prop(item, "name", text="", emboss=False, translate=False, icon=custom_icon)
        split.label(text=item.name)#, icon=custom_icon) # avoids renaming the item by accident

    def invoke(self, context, event):
        pass   

class OBJECT_PT_sl_canvas(Panel):
    """Adds a frame list panel to the object properties"""
    bl_idname = 'OBJECT_PT_sl_canvas'
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_label = "Stop Lighting Canvas"
    bl_context = "object"
    
    @classmethod
    def poll(cls, context):
        # Only draw panel for canvas objects
        return context.object.smvp_canvas.is_canvas
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        obj = context.object

        # Frame List
        row = layout.row()
        row.template_list(SL_CANVAS_UL_items.bl_idname, "", obj.smvp_canvas, "frame_list", obj.smvp_canvas, "frame_list_index", rows=4)
        # Frame Action OPs
        col = row.column(align=True)
        col.operator(SMVP_CANVAS_OT_addFrame.bl_idname, icon='ADD', text="")
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='REMOVE', text="").action = 'REMOVE'
        col.separator()
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='TRIA_UP', text="").action = 'UP'
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='TRIA_DOWN', text="").action = 'DOWN'
        # Other Frame OPs
        row = layout.row()
        col = row.column(align=True)
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_STILL", text="Capture Sequence")
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_selectFrame.bl_idname, icon="LAYER_ACTIVE", text="Select current frame")
        row.operator(SMVP_CANVAS_OT_selectFrame.bl_idname, icon="ARROW_LEFTRIGHT", text="Jump to selected").jump_to_selected = True
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_removeDuplicates.bl_idname, icon="TRASH")
        row.operator(SMVP_CANVAS_OT_clearFrames.bl_idname, icon="PANEL_CLOSE")
        
        # Other OPs for changing display modes etc?


# -------------------------------------------------------------------
# Camera UI
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Add Menu Entry
# -------------------------------------------------------------------

class OBJECT_MT_smvp_submenu(Menu):
    bl_idname = "OBJECT_MT_smvp_submenu"
    bl_label = "Stop Lighting"

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
    # Stop Lighting Sidepanel
    VIEW3D_PT_sl_scene,
    VIEW3D_PT_renderctl,
    VIEW3D_PT_domectl,

    # Canvas UI
    SL_CANVAS_UL_items,
    OBJECT_PT_sl_canvas,

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
    

