import bpy
from bpy.types import WindowManager as wm
import zmq
import time
import os
import subprocess
from threading import Thread
import numpy as np

from smvp_ipc import *

context = zmq.Context()
socket: zmq.Socket = None
connected = False
server = None
server_address = ""
receiver = None

image_requests = {}
request_count = 0

SERVER_CWD = os.path.abspath("../../")
SERVER_COMMAND = [".venv/bin/python", "server.py"]

# Operator functions
def smvpConnect(address, port, launch=False) -> bool:
    global socket
    global connected
    global server
    global server_address
    global receiver
    
    # First close any remaining connections
    smvpDisconnect()

    if launch:
        # Launch process
        try:
            server = subprocess.Popen(SERVER_COMMAND, cwd=SERVER_CWD)
            time.sleep(3)
            # Call again to connect
            if server is not None:
                return connect(address, port, False)
        except:
            print(f"SMVP Error: Can't launch server process")
    else:
        # Connect to server
        socket = context.socket(zmq.REQ)
        server_address = f"tcp://{address}:{port}"
        val = socket.connect(server_address)
        # Set timeout and disconnect after timeout option
        socket.setsockopt(zmq.RCVTIMEO, 3000)
        socket.setsockopt(zmq.LINGER, 0)
        # Send an init message and wait for answer
        message = Message(Command.Init, {})
        try:
            connected = sendMessage(message, reconnect=False, force=True) is not None
            
            if connected:
                # Launch service, receiving port is server port +1
                receiver = Thread(target=serviceRun, args=(port+1, ))
                receiver.start()
            
            return connected
        except:
            print(f"SMVP Error: Can't connect to server {server_address}")
    return False

def smvpDisconnect():
    global socket
    global connected
    global server_address

    # Only close with an active connection
    if connected:
        socket.disconnect(server_address)
        connected = False

def sendMessage(message, reconnect=True, force=False) -> Message|None:
    global socket
    global connected
    
    if not connected and reconnect:
        # Try to connect
        bpy.ops.wm.smvp_connect(launch=False)
    if connected or force:
        # Send message
        try:
            ipc.send(socket, message)
            # Receive answer
            answer = ipc.receive(socket)
            if answer.command == Command.CommandError:
                # Print error message
                print("Received error from smvp server" + f": {answer.data['message']}" if 'message' in answer.data else "")
            return answer
        except Exception as err:
            print(f"SMVP Communication error: {str(err)}")
            smvpDisconnect()
    return None


def serviceAddReq(image) -> int:
    global image_requests
    global request_count
    
    id = request_count
    request_count += 1
    image_requests[id] = image
    
    return id

def serviceRun(port):
    global connected
    global context
    global image_requests

    # Setup socket
    recv_addr = f"tcp://*:{port}"
    recv_sock = context.socket(zmq.PULL)
    recv_sock.bind(recv_addr)
    # Poller
    poller = zmq.Poller()
    poller.register(recv_sock, zmq.POLLIN)

    # Poll loop
    while connected:
        if poller.poll(500):
            # Data received
            try:
                id, img_data = receive_array(recv_sock)
                
                if id in image_requests:
                    image_requests[id].pixels.foreach_set(np.flipud(img_data).flatten())
                    # TODO: Remove ref
                else:
                    print(f"Error: ID {id} not in requested images")
            except Exception as e:
                print(f"SMVP receiver error: Can't read received data ({str(e)})")
    

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
    launch: bpy.props.BoolProperty(
        name="Launch server",
        default=False,
        description="If server process should be launched before connecting",
    )

    def execute(self, context):
        if not smvpConnect(self.address, self.port, self.launch):
            self.report({"WARNING"}, f"Can't connect to server {self.address}:{self.port}")
            return {"CANCELLED"}
        return {"FINISHED"}
    
    @classmethod
    def poll(cls, context):
        global connected
        return not connected


# register operators
def register():
    # Operators
    bpy.utils.register_class(WM_OT_smvp_connect)


def unregister():
    global server
    
    # Disconnect, stop receiver service
    smvpDisconnect()
    if receiver is not None:
        receiver.join()

    # Close server process
    if server:
        server.terminate()

    # Operators
    bpy.utils.unregister_class(WM_OT_smvp_connect)
    