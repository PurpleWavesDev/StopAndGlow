import bpy
from bpy.types import WindowManager as wm
import zmq
import subprocess
import time
import os

from smvp_ipc import *

context = zmq.Context()
socket = None
connected = False
server = None

SERVER_CWD = os.path.abspath("../")
SERVER_COMMAND = [".venv/bin/python", "server.py"]

# Operator functions
def smvpConnect(address, port, launch=True) -> bool:
    global socket
    global connected
    global server
    
    # First close any remaining connections
    smvpDisconnect()

    # Connect to server
    socket = context.socket(zmq.REQ)
    val = socket.connect(f"tcp://{address}:{port}")
    if val:
        connected = True
        return True
    elif launch:
        # Launch process
        print("Launching server process")
        server = subprocess.Popen(SERVER_COMMAND, cwd=SERVER_CWD)
        time.sleep(1)
        # Try again but this time without launching a new process
        if server is not None:
            connect(address, port, False)
    return False

def smvpDisconnect():
    global socket
    global connected
    
    # Only close with an active connection
    if connected:
        socket.disconnect()
        connected = False

def sendMessage(message) -> bool:
    global socket
    global connected
    
    # Send message
    if connected:
        ipc.send(socket, message)
        # Receive answer
        answer = ipc.receive(socket)
        if answer is not None:
            if answer.command == Command.CommandError:
                # Print error message
                print("Received error from smvp server" + f": {answer.data['message']}" if 'message' in answer.data else "")
            return answer
    return False

class WM_OT_smvp_connect(bpy.types.Operator):
    """To open an connection to the Stop Motion VP server for accessing pre-rendered or captured frames"""

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
        if not smvpConnect(self.address, self.port):
            self.report({"WARNING"}, f"Can't connect to server {self.address}:{self.port}")
            return {"CANCELLED"}
        return {"FINISHED"}

# register operators
def register():
    # Operators
    bpy.utils.register_class(WM_OT_smvp_connect)


def unregister():
    global server

    # Operators
    bpy.utils.unregister_class(WM_OT_smvp_connect)

    # Close server process
    if server:
        server.terminate()
    