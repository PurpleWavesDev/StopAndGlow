import bpy
from bpy.types import Panel

from .client import *
from .domectl import *
from .canvas import *


# -------------------------------------------------------------------
# Stop Motion VP Control
# -------------------------------------------------------------------





class VIEW3D_PT_stop_motion_vp(Panel): 

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI"  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Stop Motion"  # found in the Sidebar
    bl_label = "Stop Motion VP"  # found at the top of the Panel

    def draw(self, context):
        """define the layout of the panel"""
        row = self.layout.row()
        row.operator(OBJECT_OT_smvp_canvas_add.bl_idname, text="Create Canvas", icon ="PLUS")
        row = self.layout.row()
        row.operator("mesh.primitive_cube_add", text="Live View", icon = "SCENE")
        row = self.layout.row()
        row.operator("mesh.primitive_ico_sphere_add", text="Capture Sequence", icon = "MONKEY")
      

   

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





class VIEW3D_PT_render_agorithms(Panel): 

    bl_space_type = "VIEW_3D"  
    bl_region_type = "UI"  
    bl_parent_id = "VIEW3D_PT_stop_motion_vp"
    bl_category = "Item" 
    bl_label = "Render Algorithms"  #

    def draw(self, context):
        """define the layout of the panel"""
        row = self.layout.row()
        row.operator("object.shade_flat", text="Algorithm 1")
        row = self.layout.row()
        row.operator("object.select_random", text="Algorithm 2")
        row = self.layout.row()
        row.operator("object.shade_smooth", text="Algorithm 3")


# -------------------------------------------------------------------
# Dome Control
# -------------------------------------------------------------------

class VIEW3D_PT_domectl(Panel): 

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI" #Window  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Stop Motion"  # found in the Sidebar
    bl_label = "Lightdome controls"  # found at the top of the Panel

    def draw(self, context):
        """define the layout of the panel"""
        row = self.layout.row()
        row.operator(WM_OT_smvp_connect.bl_idname, text="Launch service")
        row = self.layout.row()
        row.operator(WM_OT_domectl_lights_on.bl_idname, text="Lights on", icon = "OUTLINER_OB_LIGHT")
        row = self.layout.row()
        row.operator(WM_OT_domectl_lights_off.bl_idname, text="Lights off", icon = "OUTLINER_DATA_LIGHT")

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
        col.operator(SMVP_CANVAS_OT_addFrame.bl_idname, icon='ZOOM_IN', text="")
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='ZOOM_OUT', text="").action = 'REMOVE'
        col.separator()
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='TRIA_UP', text="").action = 'UP'
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='TRIA_DOWN', text="").action = 'DOWN'

        row = layout.row()
        col = row.column(align=True)
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_printFrames.bl_idname, icon="LINENUMBERS_ON")
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_selectFrame.bl_idname, icon="VIEW3D", text="Select current frame")
        row.operator(SMVP_CANVAS_OT_selectFrame.bl_idname, icon="GROUP", text="Jump to selected").jump_to_selected = True
        row = col.row(align=True)
        row.operator(SMVP_CANVAS_OT_clearFrames.bl_idname, icon="X")
        row.operator(SMVP_CANVAS_OT_removeDuplicates.bl_idname, icon="GHOST_ENABLED")


# -------------------------------------------------------------------
# un/register
# -------------------------------------------------------------------

CLASSES =[
    
    # Stop Motion VP
    VIEW3D_PT_stop_motion_vp,
    VIEW3D_PT_onionskin,
    VIEW3D_PT_render_agorithms,
    # Dome Control
    VIEW3D_PT_domectl,
    # Canvas UI
    SMVP_CANVAS_UL_items,
    SMVP_CANVAS_PT_frameList,

]

def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    

def unregister():
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
    
    