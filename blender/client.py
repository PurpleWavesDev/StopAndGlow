import bpy
from bpy.types import WindowManager as wm
import zmq

context = zmq.Context()
socket = None
connected = False

# Properties
class ConnectionProperties(bpy.types.PropertyGroup):
    connected: bpy.props.BoolProperty()
    #socket: bpy.props.GenericType

# Operator functions
def connect(address, port):
    global socket
    global connected
    
    # First close any remaining connections
    disconnect()

    # Connect to server
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{address}:{port}")
    if socket:
        socket.send(b"Hello world from Python!")
        connected = True
        #wm.smvp_con.socket = socket
        return True
    return False

def disconnect():
    global socket
    global connected
    
    # Only close with an active connection
    if connected:
        socket.disconnect()
        connected = False

class WM_OT_smvp_connect(bpy.types.Operator):
    """Create a new monkey mesh object with a subdivision surf modifier and shaded smooth"""

    bl_idname = "wm.smvp_connect"
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
        description="Port of connection",
    )

    def execute(self, context):
        if not connect(self.address, self.port):
            return {"CANCELLED"}
        return {"FINISHED"}

# register operators
def register():
    # Properties
    bpy.utils.register_class(ConnectionProperties)
    #bpy.types.plugins. = bpy.props.PointerProperty(type=ConnectionProperties)
    # Operators
    bpy.utils.register_class(WM_OT_smvp_connect)


def unregister():
    # Properties
    bpy.utils.unregister_class(ConnectionProperties)
    # Operators
    bpy.utils.unregister_class(WM_OT_smvp_connect)
