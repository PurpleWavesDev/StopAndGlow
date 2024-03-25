import bpy
from bpy.types import Scene, Object, Camera, PropertyGroup
from bpy.props import *



class SMVP_SceneProps(PropertyGroup):
    active_canvas: StringProperty()
    canvas_ids: IntProperty()

class SMVP_CANVAS_FrameCollection(PropertyGroup):
    #name: StringProperty() -> Instantiated by default
    seq_path: StringProperty()
    id: IntProperty()
    
    rendered_texture: StringProperty()
    preview_texture: StringProperty()
    
    updated: BoolProperty(default=False)
    preview_updated: BoolProperty(default=False)

class SMVP_CanvasProps(PropertyGroup):
    is_canvas: BoolProperty()
    frame_list_index: IntProperty()
    frame_list: CollectionProperty(type=SMVP_CANVAS_FrameCollection)
    
    display_preview: BoolProperty(default=True)
    render_type: StringProperty()
    exposure: FloatProperty()
    preview_exposure: FloatProperty()
    
    canvas_id: IntProperty()
    frame_ids: IntProperty()
    

class SMVP_CameraProps(PropertyGroup):
    canvas_link: StringProperty()


def get_algorithms(self, context):

    items = [
        ("id00", "Default", ""),
    ]

    for i in range(7):
    
        name = "0"+str(i+1)

        items.append(("id"+str(i+1), "Algorithm."+ name, "")),
    
    return items

class SMVP_Algorithms_Props(PropertyGroup):
    
    algs_dropdown_items : bpy.props.EnumProperty(
        name= "Algorithms",
        description= "description",
        items= get_algorithms
    )
   

def update_function(self, context):
    if self.toggle_render_algs:
        bpy.ops.algs.render('INVOKE_DEFAULT')
    return

classes = (
    SMVP_SceneProps,
    SMVP_CANVAS_FrameCollection,
    SMVP_CanvasProps,
    SMVP_CameraProps,
    SMVP_Algorithms_Props
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    # Assign properties
    Scene.smvp_scene = PointerProperty(type=SMVP_SceneProps, name="SMVP Scene Properties")
    Object.smvp_canvas = PointerProperty(type=SMVP_CanvasProps, name="SMVP Canvas Properties")
    Camera.smvp = PointerProperty(type=SMVP_CameraProps, name="SMVP Camera Properties")

     # Add Render Algorithm PointerProperty 
    Scene.smvp_algorithms = PointerProperty(type= SMVP_Algorithms_Props)

    # Toggle Render Algorithms Button    
    bpy.types.WindowManager.toggle_render_algs = bpy.props.BoolProperty(
                                                    default = False,
                                                    update = update_function)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    # Delete properties
    del Scene.smvp_scene
    del Object.smvp_canvas
    del Camera.smvp

    #del Scene.smvp_algorithms
    del bpy.types.Scene.smvp_algorithms

    #del Toggle Button
    del bpy.types.WindowManager.toggle_render_algs
