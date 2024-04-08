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
        split = layout.split(factor=0.4)
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
        split = layout.split(factor=0.4)
        split.label(text="Scene Setup")
        split.operator(OBJECT_OT_smvpCanvasAdd.bl_idname, text="New", icon ="PLUS")


# -------------------------------------------------------------------
# Capture & Display: Capture, Display Modes, Render Algorithms and Ghosting
# -------------------------------------------------------------------        
            
class VIEW3D_PT_sl_canvas(bpy.types.Panel):
    """Display settings for the active Stop Lighting Canvas"""
    bl_label = "Canvas"
    bl_idname = "VIEW3D_PT_sl_canvas"
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

        # Display modes
        row = layout.row()
        row.label(text="Display Modes")
        row.prop(obj.smvp_canvas,'display_mode',expand = True)
        # Update lighting
        if obj.smvp_canvas.display_mode == 'bake':
            row = layout.row()
            row.operator(SMVP_CANVAS_OT_updateScene.bl_idname, icon="RECOVER_LAST", text="Update Lighting")
        # Algorithm
        elif obj.smvp_canvas.display_mode == 'rend':
            row = layout.row()
            row.prop(algs, "algs_dropdown_items", expand=False, text="")
            #row = layout.row()
            row.operator(SMVP_CANVAS_OT_applyRenderAlgorithm.bl_idname, text="Apply")  
        
        # Ghosting
        ghostIcon =  "GHOST_ENABLED" if obj.smvp_ghost.show_ghost else "GHOST_DISABLED"
        ghostLabel = "Hide Ghostframes" if obj.smvp_ghost.show_ghost else "Display Ghostframes"
        layout.separator()
        header, panel = self.layout.panel("sl_ghosting_id", default_closed=True)
        header.operator(SMVP_CANVAS_OT_setGhostMode.bl_idname, icon=ghostIcon, text="")
        header.label(text="Ghost Frames")
        if panel:
            row = panel.row()
            row.label(text="Previous")
            row.prop(obj.smvp_ghost, "previous_frames", text="")

            row = panel.row()
            row.label(text="Post")
            row.prop(obj.smvp_ghost, "following_frames", text="") 
            row = panel.row()
            row.prop(obj.smvp_ghost, "opacity", text= "Opacity", slider = True)
        
        # Capturing
        layout.separator()
        row = layout.row()
        row.label(text="Capture")
        row = layout.row(align=True)
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_ANIMATION", text="Sequence")
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_STILL", text="Baked").baked=True
            
  
# -------------------------------------------------------------------
# Service / Hardware Control
# -------------------------------------------------------------------

class VIEW3D_PT_sl_ctl(Panel): 

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI" #Window  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Stop Lighting"  # found in the Sidebar
    bl_label = "Controls"  # found at the top of the Panel
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout
        # Lights
        split = lay.split(factor=0.4, align=True)
        split.label(text="Lights")
        split.operator(WM_OT_smvp_lightctl.bl_idname, text="On", icon = "OUTLINER_OB_LIGHT").light_state = "TOP"
        split.operator(WM_OT_smvp_lightctl.bl_idname, text="Off", icon = "OUTLINER_DATA_LIGHT").light_state = "OFF"
        
        # Camera
        lay.separator()
        header, panel = lay.panel("sl_camera_id", default_closed=False)
        header.label(text="Camera")
        if panel:
            pass
        
        # Server
        lay.separator()
        header, panel = lay.panel("sl_server_id", default_closed=False)
        header.label(text="Server")
        if panel:
            split = panel.split(factor=0.4, align=True)
            split.label(text="Connected" if context.scene.smvp_scene.connected else "Disconnected")
            split.operator(WM_OT_smvp_connect.bl_idname, text="Connect")
            split.operator(WM_OT_smvp_launch.bl_idname, text="Launch")



# -------------------------------------------------------------------
# Canvas UI
# -------------------------------------------------------------------

class SL_CANVAS_UL_frames(UIList):
    bl_idname = 'SL_CANVAS_UL_frames'
    
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
        row.template_list(SL_CANVAS_UL_frames.bl_idname, "", obj.smvp_canvas, "frame_list", obj.smvp_canvas, "frame_list_index", rows=4)
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
        row.operator(SMVP_CANVAS_OT_selectFrame.bl_idname, icon="LAYER_ACTIVE", text="Select current frame")
        row.operator(SMVP_CANVAS_OT_selectFrame.bl_idname, icon="ARROW_LEFTRIGHT", text="Jump to selected").jump_to_selected = True
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_removeDuplicates.bl_idname, icon="TRASH")
        row.operator(SMVP_CANVAS_OT_clearFrames.bl_idname, icon="PANEL_CLOSE")
        # Capture OPs
        row = layout.row(align=True)
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_ANIMATION", text="Capture Sequence")
        row.operator(SMVP_CANVAS_OT_capture.bl_idname, icon="RENDER_STILL", text="Capture Baked").baked=True
        
        # Other OPs for changing display modes etc?


# -------------------------------------------------------------------
# Camera UI
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Add Menu Entry
# -------------------------------------------------------------------

class OBJECT_MT_sl_submenu(Menu):
    bl_idname = "OBJECT_MT_sl_submenu"
    bl_label = "Stop Lighting"

    def draw(self, context):
        layout = self.layout
        layout.operator(OBJECT_OT_smvpCanvasAdd.bl_idname, text="Canvas", icon="IMAGE_PLANE")
        layout.operator(SMVP_CAMERA_OT_addLinked.bl_idname, text="Linked Camera", icon="VIEW_CAMERA")
    
        
def smvp_objects_menu(self, context):
    self.layout.separator()
    self.layout.menu(OBJECT_MT_sl_submenu.bl_idname, text="SMVP", icon="GHOST_DISABLED")



# -------------------------------------------------------------------
# un/register
# -------------------------------------------------------------------

classes =(
    # Stop Lighting Sidepanel
    VIEW3D_PT_sl_scene,
    VIEW3D_PT_sl_canvas,
    VIEW3D_PT_sl_ctl,

    # Canvas UI
    SL_CANVAS_UL_frames,
    OBJECT_PT_sl_canvas,

    # Menus
    OBJECT_MT_sl_submenu,
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
    

