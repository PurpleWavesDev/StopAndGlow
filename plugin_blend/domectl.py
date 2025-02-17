# Hardware and server related operators

import bpy

from sng_ipc import *
from . import client


class WM_OT_sng_connect(bpy.types.Operator):
    """Connect to Stop Motion VP Server"""

    bl_idname = "wm.sng_connect"
    bl_label = "Connect to Stop Motion VP Server"
    bl_options = {"REGISTER"}

    address: bpy.props.StringProperty(
        name="Address",
        default="localhost",
        description="Host address to connect to",
    )
    port: bpy.props.IntProperty(
        name="Port",
        default=9271,
        description="Port the service should use",
    )

    def execute(self, context):
        if not client.smvpConnect(self.address, self.port):
            self.report({"WARNING"}, f"Can't connect to server {self.address}:{self.port}")
            return {"CANCELLED"}
        return {"FINISHED"}
    
class WM_OT_sng_launch(bpy.types.Operator):
    """Launches the Stop Motion VP service"""

    bl_idname = "wm.sng_launch"
    bl_label = "Launch Stop Motion VP Service"
    bl_options = {"REGISTER"}

    port: bpy.props.IntProperty(
        name="Port",
        default=9271,
        description="Port of connection",
    )

    def execute(self, context):
        if not client.smvpLaunch(self.port):
            self.report({"WARNING"}, f"Failed to launch service")
            return {"CANCELLED"}
        return {"FINISHED"}
    
    @classmethod
    def poll(cls, context):
        return not context.scene.sng_scene.connected


class WM_OT_sng_lightctl(bpy.types.Operator):
    """To open an connection to the Stop Motion VP server for accessing pre-rendered or captured frames"""

    bl_idname = "wm.sng_lightctl"
    bl_label = "Set the state of the lights of the dome"
    bl_options = {"REGISTER", "UNDO"}
    
    light_state: bpy.props.EnumProperty(items=[
        ("TOP", "Top", "", 1),
        ("RING", "Ring", "", 2),
        ("RAND", "Rand", "", 3),
        ("OFF", "Off", "", 4),
        ])
    power: bpy.props.FloatProperty(name="Power", default=0.3, min=0.0, max=1.0, step=5)
    amount: bpy.props.FloatProperty(name="Amount", default=0.3, min=0.0, max=1.0, step=5)
    width: bpy.props.FloatProperty(name="Ring Width", default=0.25, min=0.0, max=1.0, step=5)

    def execute(self, context):
        command = None
        match self.light_state:
            case 'TOP':
                command = Command.LightCtlTop
            case 'RING':
                command = Command.LightCtlRing
            case 'RAND':
                command = Command.LightCtlRand
            case 'OFF':
                command = Command.LightCtlOff
        message = Message(command, {'power': self.power, 'amount': self.amount, 'width': self.width})
        client.sendMessage(message)
        return {"FINISHED"}
    
class WM_OT_sng_viewer(bpy.types.Operator):
    """To open the (live) viewer of the server"""

    bl_idname = "wm.sng_viewer"
    bl_label = "Open the viewer on the server"
    bl_options = {"REGISTER"}

    def execute(self, context):
        message = Message(Command.ViewerLaunch)
        client.sendMessage(message)
        return {"FINISHED"}


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    WM_OT_sng_connect,
    WM_OT_sng_launch,
    WM_OT_sng_lightctl,
    WM_OT_sng_viewer,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

