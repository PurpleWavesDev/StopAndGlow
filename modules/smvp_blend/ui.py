# Blender Add-on Template
# Contributor(s): Aaron Powell (aaron@lunadigital.tv)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.types import Panel

from .client import *
from .domectl import *
from .canvas import *


#
# Add additional functions here
#

class VIEW3D_PT_render_agorithms(Panel): 

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI"  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Item"  # found in the Sidebar
    bl_label = "Render Algorithms"  # found at the top of the Panel

    def draw(self, context):
        """define the layout of the panel"""
        row = self.layout.row()
        row.operator("object.shade_flat", text="Algorithm 1")
        row = self.layout.row()
        row.operator("object.select_random", text="Algorithm 2")
        row = self.layout.row()
        row.operator("object.shade_smooth", text="Algorithm 3")




class VIEW3D_PT_stop_motion_vp(Panel): 

    # where to add the panel in the UI
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI"  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Stop Motion"  # found in the Sidebar
    bl_label = "Stop Motion VP"  # found at the top of the Panel

    def draw(self, context):
        """define the layout of the panel"""
        row = self.layout.row()
        row.operator(OBJECT_OT_smvp_canvas_add.bl_idname, text="Create Canvas")
        row = self.layout.row()
        row.operator("mesh.primitive_cube_add", text="Toggle Live View")
        row = self.layout.row()
        row.operator("mesh.primitive_ico_sphere_add", text="Capture Frame")
        row = self.layout.row()
        row.operator("object.shade_smooth", text="Show Ghosting")

   

class VIEW3D_PT_onionskin(Panel):
    bl_space_type = "VIEW_3D"  # 3D Viewport area (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/space_type_items.html#rna-enum-space-type-items)
    bl_region_type = "UI"  # Sidebar region (find list of values here https://docs.blender.org/api/current/bpy_types_enum_items/region_type_items.html#rna-enum-region-type-items)

    bl_category = "Stop Motion"  # found in the Sidebar
    bl_label = "Show Ghosting"  # found at the top of the Panel
    bl_parent_id = "VIEW3D_PT_stop_motion_vp"

    def draw_header(self,context):
        # Example property to display a checkbox, can be anything
            self.layout.prop(context.scene.render, "use_border", text="")

    def draw(self, context):        
        self.layout.label(text="Framerange", icon='WORLD_DATA')
        row = self.layout.row()
        row.prop(context.scene, "frame_start", text = "previous Frames")
        row.prop(context.scene, "frame_end", text = "following Frames") 



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
        row.operator(WM_OT_domectl_lights_on.bl_idname, text="Lights on")
        row = self.layout.row()
        row.operator(WM_OT_domectl_lights_off.bl_idname, text="Lights off")

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
        col.operator(SMVP_CANVAS_OT_actions.bl_idname, icon='ZOOM_IN', text="").action = 'ADD'
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


CLASSES =[
    
    VIEW3D_PT_render_agorithms,
    VIEW3D_PT_stop_motion_vp,
    VIEW3D_PT_domectl,
    VIEW3D_PT_onionskin,
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
    
    