import bpy


class VIEW3D_PT_stop_motion_vp(bpy.types.Panel):

    bl_idname = "VIEW3D_PT_layout"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_context = "interface"
    bl_category = "Stop Motion"
    bl_label = "Stop Motion VP"

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        # Create a simple row.
        layout.label(text="Simple Row:")

        row = layout.row()
        row.prop(scene, "frame_start", text = "test")
        row.prop(scene, "frame_end")
        
        row = self.layout.row()
        row.operator("mesh.primitive_cube_add", text="Add Cube")

       


class VIEW3D_PT_stop_motion_sub1(bpy.types.Panel):
    bl_parent_id = "VIEW3D_PT_layout"    
    bl_idname = "VIEW3D_VP_subpanel_1"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    #bl_context = "interface"
    bl_category = "Stop Motion"
    bl_label = "Camera Settings"

    def draw(self, context):
        layout = self.layout
        
        scene = context.scene
        
 # Create an row where the buttons are aligned to each other.
        layout.label(text="Aligned Row:")

        row = layout.row(align=True)
        row.prop(scene, "frame_start")
        row.prop(scene, "frame_end")

        # Create two columns, by using a split layout.
        split = layout.split()

        # First column
        col = split.column()
        col.label(text="Column One:")
        col.prop(scene, "frame_end")
        col.prop(scene, "frame_start")

        # Second column, aligned
        col = split.column(align=True)
        col.label(text="Column Two:")
        col.prop(scene, "frame_start")
        col.prop(scene, "frame_end")

        # Big render button
       # layout.label(text="Big Button:")
        row = layout.row()
        row.scale_y = 3.0
        row.operator("render.render")

        # Different sizes in a row
        layout.label(text="Different button sizes:")
        row = layout.row(align=True)
        row.operator("render.render")

        sub = row.row()
        sub.scale_x = 2.0
        sub.operator("render.render")

        row.operator("render.render")


class VIEW3D_PT_stop_motion_sub2(bpy.types.Panel):
    bl_parent_id = "VIEW3D_PT_layout"    
    bl_idname = "VIEW3D_VP_subpanel_2"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    #bl_context = "interface"
    bl_category = "Stop Motion"
    bl_label = "Live Viewer"

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        # Create a simple row.
        layout.label(text="Simple Row:")

        row = layout.row()
        row.prop(scene, "frame_start", text = "test")
        row.prop(scene, "frame_end")
        
        row = self.layout.row()
        row.operator("mesh.primitive_cube_add", text="Add Cube")

        # Create an row where the buttons are aligned to each other.
        layout.label(text="Aligned Row:")

        row = layout.row(align=True)
        row.prop(scene, "frame_start")
        row.prop(scene, "frame_end")

        # Create two columns, by using a split layout.
        split = layout.split()

        # First column
        col = split.column()
        col.label(text="Column One:")
        col.prop(scene, "frame_end")
        col.prop(scene, "frame_start")

 
 
 
        
CLASSES = [
    VIEW3D_PT_stop_motion_vp,
    VIEW3D_PT_stop_motion_sub1,
    VIEW3D_PT_stop_motion_sub2,
    ]



def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
