import bpy
from bpy.types import Scene, Object, Camera, PropertyGroup
from bpy.props import *

from sng_ipc import *

from . import client

## Lists for properties (static & dynamic)
algorithms = []
display_modes = [
        ('prev', '', 'Preview',"SHADING_SOLID", 0),
        ('live', '', 'Live View', "SCENE", 1),
        ('baked', '', 'Baked Lights', "LIGHT", 2), # LIGHT / SHADING_TEXTURE / MATERIAL?
        ('rend', '', 'Rendered', "SHADING_RENDERED", 3),
    ]

## Property functions and callbacks
def DisplayModeProp(callback=None):
    return EnumProperty(items=display_modes, name='Display Modes', default='prev', update=callback) # update or set

def DisplayModeUpdate(self, context):
    # Call operator
    bpy.ops.sng_canvas.display_mode(display_mode=self.display_mode)

## Property pollers
def IsCanvasPoll(self, obj):
    return obj.sng_canvas.is_canvas
    


## Property classes
class SNG_SceneProps(PropertyGroup):
    # Settings
    resolution: IntVectorProperty(size=2, default=(1920, 1080))
    update_rate: FloatProperty(default=5.0)
    # Internal props
    canvas_ids: IntProperty()
    connected: BoolProperty(get=lambda self: client.connected)
    # Camera for environment renders
    render_cam: StringProperty()

class SNG_CANVAS_FrameCollection(PropertyGroup):
    #name: StringProperty() -> Instantiated by default
    seq_path: StringProperty()
    id: IntProperty()
    
    render_texture: StringProperty()
    preview_texture: StringProperty()
    
    preview_updated: BoolProperty(default=False)
    texture_updated: BoolProperty(default=False)

class SNG_CanvasProps(PropertyGroup):
    is_canvas: BoolProperty()
    frame_list_index: IntProperty()
    frame_list: CollectionProperty(type=SNG_CANVAS_FrameCollection)
    canvas_texture: StringProperty()
    ghost_texture: StringProperty()
    
    display_mode: DisplayModeProp(DisplayModeUpdate)
    render_type: StringProperty()
    #exposure: FloatProperty()
    
    canvas_id: IntProperty()
    frame_ids: IntProperty()
    
    env_tex_path: StringProperty()





def ghost_update_func(self, context):
    print("invoke modal")
    if self.ghost_toggle:
        VIEW3D_OT_modalGhosting.bl_idname('INVOKE_DEFAULT')
    return

class SNG_GhostProps(PropertyGroup):
      
    show_ghost: BoolProperty(
        name="Show Ghostframes", 
        description="Toggle the display of frames before and/or after the current frame", 
        default = False,
        )
    previous_frames: IntProperty(
        name="Previous Frames", 
        description="Defines the number of previous frames displayed in Ghost Mode", 
        default=10, min=0, soft_max=20, step=1
        )
    following_frames: IntProperty(
        name="Following Frames",
        description="Defines the number of following frames displayed in Ghost Mode",
        default=10, min=0, soft_max=20, step=1
        )
    opacity: FloatProperty(
        name="Ghost Opacity", 
        description= "Opacity of Ghostframes", 
        default=0.5, min=0.0, max=1.0, step=1
        )
    falloff: FloatProperty()


class SNG_CameraProps(PropertyGroup):
    canvas_link: StringProperty()


def getAlgorithms(self, context) -> list:
    """Returns a list of available render algorithms but only when a connection to the server is established"""
    global algorithms
    
    if not algorithms and context.scene.sng_scene.connected:
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
    if context.scene.sng_scene.connected:
        message = Message(Command.Command.GetRenderSettings)
        answer = client.sendMessage(message)
        if answer.command == Command.CommandAnswer:
            return answer.data
    return {}

class SNG_Algorithms_Props(PropertyGroup):
    
    algs_dropdown_items : bpy.props.EnumProperty(
        name="Algorithms",
        description="Algorithms for rendering",
        items=getAlgorithms
    )
   


classes = (
    SNG_SceneProps,
    SNG_CANVAS_FrameCollection,
    SNG_CanvasProps,
    SNG_CameraProps,
    SNG_Algorithms_Props,
    SNG_GhostProps
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    # Register custom object types (defined thorugh pollers)
    bpy.types.Scene.sl_canvas = bpy.props.PointerProperty(
        type=bpy.types.Object,
        poll=IsCanvasPoll
    )

    
    # Assign properties
    Scene.sng_scene = PointerProperty(type=SNG_SceneProps, name="SMVP Scene Properties")
    Object.sng_canvas = PointerProperty(type=SNG_CanvasProps, name="SMVP Canvas Properties")
    Camera.smvp = PointerProperty(type=SNG_CameraProps, name="SMVP Camera Properties")
    Scene.sng_algorithms = PointerProperty(type=SNG_Algorithms_Props, name="Algorithms Properties")
    Object.sng_ghost = PointerProperty(type= SNG_GhostProps, name="Ghosting Properties")


   

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    # Delete properties
    del Scene.sng_scene
    del Object.sng_canvas
    del Camera.smvp
    del Scene.sng_algorithms

    del bpy.types.WindowManager.ghost_toggle

   
