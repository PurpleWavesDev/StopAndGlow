import bpy

from smvp_ipc import *
from .client import sendMessage

class WM_OT_domectl_lights_on(bpy.types.Operator):
    """To open an connection to the Stop Motion VP server for accessing pre-rendered or captured frames"""

    bl_idname = "wm.smvp_lightctl_on"
    bl_label = "Connect to Stop Motion VP Server"
    bl_options = {"REGISTER"}

    def execute(self, context):
        message = Message.LightCtlMsg(Command.LightCtlRand)
        sendMessage(message)
        return {"FINISHED"}
    
class WM_OT_domectl_lights_off(bpy.types.Operator):
    """To open an connection to the Stop Motion VP server for accessing pre-rendered or captured frames"""

    bl_idname = "wm.smvp_lightctl_on"
    bl_label = "Connect to Stop Motion VP Server"
    bl_options = {"REGISTER"}

    def execute(self, context):
        message = Message.LightCtlMsg(Command.LightCtlOff)
        sendMessage(message)
        return {"FINISHED"}


# register operators
def register():
    # Operators
    bpy.utils.register_class(WM_OT_domectl_lights_on)
    bpy.utils.register_class(WM_OT_domectl_lights_off)


def unregister():
    # Operators
    bpy.utils.unregister_class(WM_OT_domectl_lights_on)
    bpy.utils.unregister_class(WM_OT_domectl_lights_off)

    