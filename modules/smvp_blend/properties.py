import bpy
from bpy.types import Scene, Object, Camera, PropertyGroup
from bpy.props import *

from smvp_ipc import *

from . import client

algorithms = []
display_modes = [
        ('prev', '', 'Preview',"SHADING_SOLID", 0),
        ('bake', '', 'Baked Lights', "SHADING_TEXTURE",1),
        ('rend', '', 'Rendered', "SHADING_RENDERED",2),
        ('live', '', 'Live View', "SCENE", 3)
    ]

def DisplayModeProp(callback=None):
    return EnumProperty(items=display_modes, name='Display Modes', default='prev', update=callback) # update or set

class SMVP_SceneProps(PropertyGroup):
    active_canvas: StringProperty()
    canvas_ids: IntProperty()
    resolution: IntVectorProperty(size=2, default=(1920, 1080))

class SMVP_CANVAS_FrameCollection(PropertyGroup):
    #name: StringProperty() -> Instantiated by default
    seq_path: StringProperty()
    id: IntProperty()
    
    render_texture: StringProperty()
    preview_texture: StringProperty()
    
    preview_updated: BoolProperty(default=False)
    texture_updated: BoolProperty(default=False)

def DisplayModeUpdate(self, context):
    # Call operator
    bpy.ops.smvp_canvas.display_mode(display_mode=self.display_mode)

    
class SMVP_CanvasProps(PropertyGroup):
    is_canvas: BoolProperty()
    frame_list_index: IntProperty()
    frame_list: CollectionProperty(type=SMVP_CANVAS_FrameCollection)
    live_texture: StringProperty()
    
    display_mode: DisplayModeProp(DisplayModeUpdate)
    render_type: StringProperty()
    exposure: FloatProperty()
    
    canvas_id: IntProperty()
    frame_ids: IntProperty()

class SMVP_GhostProps(PropertyGroup):
    show_ghost: BoolProperty(name="Show Ghostframes", description="Toggle the display of frames before and/or after the current frame", default = False)
    previous_frames: IntProperty(name="Previous Frames", description="Defines the number of previous frames displayed in Ghost Mode", default=3, min=0, max=10, step=1)
    following_frames: IntProperty(name="Following Frames", description="Defines the number of following frames displayed in Ghost Mode", default=3, min=0, max=10, step=1)
    opacity: FloatProperty(name="Ghost Opacity", description= "Opacity of Ghostframes", default=0.5, min=0.0, max=1.0, step=1)
    falloff: FloatProperty()
    

class SMVP_CameraProps(PropertyGroup):
    canvas_link: StringProperty()


def getAlgorithms(self, context) -> list:
    """Returns a list of available render algorithms but only when a connection to the server is established"""
    global algorithms
    
    if not algorithms and client.connected:
        message = Message(Command.GetRenderAlgorithms)
        answer = client.sendMessage(message)
        if answer.command == Command.CommandAnswer:
            try:
                for name_short, name_long in answer.data['algorithms']:
                    algorithms.append((name_short, name_long, ""))
            except:
                pass
    
    return algorithms

def getAlgorithmSettings(self, context) -> dict:
    """Returns the options of the renderer/algorithm"""
    if client.connected:
        message = Message(Command.Command.GetRenderSettings)
        answer = client.sendMessage(message)
        if answer.command == Command.CommandAnswer:
            return answer.data
    return {}

class SMVP_Algorithms_Props(PropertyGroup):
    
    algs_dropdown_items : bpy.props.EnumProperty(
        name= "",
        description= "description",
        items= getAlgorithms
    )
   


classes = (
    SMVP_SceneProps,
    SMVP_CANVAS_FrameCollection,
    SMVP_CanvasProps,
    SMVP_CameraProps,
    SMVP_Algorithms_Props,
    SMVP_GhostProps
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    # Assign properties
    Scene.smvp_scene = PointerProperty(type=SMVP_SceneProps, name="SMVP Scene Properties")
    Object.smvp_canvas = PointerProperty(type=SMVP_CanvasProps, name="SMVP Canvas Properties")
    Camera.smvp = PointerProperty(type=SMVP_CameraProps, name="SMVP Camera Properties")
    Scene.smvp_algorithms = PointerProperty(type= SMVP_Algorithms_Props, name="Algorithms Properties")
    Object.smvp_ghost = PointerProperty(type= SMVP_GhostProps, name="Ghosting Properties")



def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    # Delete properties
    del Scene.smvp_scene
    del Object.smvp_canvas
    del Camera.smvp
    del Scene.smvp_algorithms

   
