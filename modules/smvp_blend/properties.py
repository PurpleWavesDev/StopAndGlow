import bpy
from bpy.types import Scene, PropertyGroup
from bpy.props import *


class SMVP_CANVAS_FrameCollection(PropertyGroup):
    #name: StringProperty() -> Instantiated by default
    obj_type: StringProperty()
    obj_id: IntProperty()
    
    seq_path: StringProperty()
    rendered_texture: StringProperty()
    preview_texture: StringProperty()
    
    updated: BoolProperty(default=False)
    preview_updated: BoolProperty(default=False)

class SMVP_CANVAS_Props(PropertyGroup):
    is_canvas: BoolProperty()
    frame_list_index: IntProperty()
    frame_list: CollectionProperty(type=SMVP_CANVAS_FrameCollection)
    
    display_preview: BoolProperty()
    render_type: StringProperty()
    exposure: FloatProperty()
    preview_exposure: FloatProperty()

classes = (
    SMVP_CANVAS_FrameCollection,
    SMVP_CANVAS_Props,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    # Assign properties
    #Scene.smvp_config = bpy.props.PointerProperty(type=SmvpConfig, name="SMVP Configuration")
    bpy.types.Object.smvp_canvas = bpy.props.PointerProperty(type=SMVP_CANVAS_Props, name="SMVP Canvas")

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    # Delete properties
    #del Scene.smvp_config
    del bpy.types.Object.smvp_canvas
