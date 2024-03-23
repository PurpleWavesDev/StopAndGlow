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
def smvpLaunch(port=0) -> bool:
    global server
    # Launch process
    try:
        command = SERVER_COMMAND if port == 0 else SERVER_COMMAND + ["--port", str(port)]
        server = subprocess.Popen(command, cwd=SERVER_CWD)
        return server is not None
    except Exception as e:
        print(f"SMVP Error: Can't launch server process ({str(e)})")
    return False

def smvpConnect(address, port) -> bool:
    global socket
    global connected
    global server
    global server_address
    global receiver
    
    # First close any remaining connections
    smvpDisconnect()

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
    


def register():
    pass


def unregister():
    global server
    
    # Disconnect, stop receiver service
    smvpDisconnect()
    if receiver is not None:
        receiver.join()

    # Close server process
    if server:
        server.terminate()

    