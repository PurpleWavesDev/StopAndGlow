import time
from threading import Thread, Lock
import subprocess
import os

import bpy
from bpy.types import WindowManager as wm
import numpy as np

import zmq
import socket
from smvp_ipc import *

context = None
send_sock = None
connected = False
server = None

receiver = None
receiver_lock = Lock()

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
    global context
    global send_sock
    global connected
    global server
    global receiver
    
    # First close any remaining connections
    smvpDisconnect()

    # Connect to server
    send_sock = context.socket(zmq.REQ)
    server_address = f"tcp://{address}:{port}"
    val = send_sock.connect(server_address)
    # Set timeout and disconnect after timeout option
    send_sock.setsockopt(zmq.RCVTIMEO, 10000)
    send_sock.setsockopt(zmq.LINGER, 0)
    # Send an init message and wait for answer
    message = Message(Command.Init, {'address': getHostname()})
    try:
        connected = sendMessage(message, reconnect=False, force=True) is not None
        
        if connected:
            # Launch service, receiving port is server port +1
            receiver = Thread(target=serviceRun, args=(port+1, ))
            receiver.start()
        
        return connected
    except:
        pass
    print(f"SMVP Error: Can't connect to server {server_address}")
    return False

def smvpDisconnect():
    global send_sock
    global connected
    global receiver

    # Only close with an active connection
    if connected:
        connected = False
        send_sock.close()
        # Wait for receiver to finish
        if receiver is not None:
            receiver.join()

def sendMessage(message, reconnect=True, force=False) -> Message|None:
    global send_sock
    global connected
    
    if not connected and reconnect:
        # Try to connect
        bpy.ops.wm.smvp_connect()
    if connected or force:
        # Send message
        try:
            ipc.send(send_sock, message)
            # Receive answer
            answer = ipc.receive(send_sock)
            if answer.command == Command.CommandError:
                # Print error message
                print("Received error from smvp server" + f": {answer.data['message']}" if 'message' in answer.data else "")
            return answer
        except Exception as err:
            print(f"SMVP Communication error: {str(err)}")
            smvpDisconnect()
    return None


def serviceAddReq(image_name) -> int:
    global image_requests
    global request_count
    
    # Delete old entry
    old_ids = [id for id, img in image_requests.items() if img == image_name]
    for id in old_ids:
        del image_requests[id]
    
    # Add new ID
    id = request_count
    request_count += 1
    image_requests[id] = image_name
    
    return id

def serviceRun(port):
    global connected
    global context
    global image_requests
    global receiver_lock 

    with receiver_lock:
        # Setup socket
        recv_addr = f"tcp://*:{port}"
        recv_sock = context.socket(zmq.REP)
        recv_sock.bind(recv_addr)
        # Set timeout and disconnect after timeout option
        recv_sock.setsockopt(zmq.LINGER, 0)

        # Poller
        poller = zmq.Poller()
        poller.register(recv_sock, zmq.POLLIN)

        while connected:
            # Poll loop
            if poller.poll(500):
                # Data received
                try:
                    id, img_data = receive_array(recv_sock)
                    
                    if not id in image_requests:
                        # ID got removed, send stop
                        ipc.send(recv_sock, Message(Command.RecvStop))
                    elif not image_requests[id] in bpy.data.images:
                        # Image messing
                        ipc.send(recv_sock, Message(Command.RecvStop))
                        print(f"SMVP receiver warning: Image {image_requests[id]} not found")
                    else:
                        # Update image, send okay
                        bpy.data.images[image_requests[id]].pixels.foreach_set(np.flipud(img_data).flatten())
                        bpy.data.images[image_requests[id]].update_tag()
                        ipc.send(recv_sock, Message(Command.RecvOkay))
                except Exception as e:
                    # Send error
                    ipc.send(recv_sock, Message(Command.RecvError, {'message': str(e)}))
                    print(f"SMVP receiver error: Can't read received data ({str(e)})")
    
        # Clean up connection
        recv_sock.close()

def getHostname():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
    return s.getsockname()[0]


def register():
    global context
    context = zmq.Context()


def unregister():
    global server
    global context
    # Disconnect, stop receiver service
    smvpDisconnect()
    if context is not None:
        context.destroy()
    if receiver is not None:
        receiver.join()

    # Close server process
    if server:
        server.terminate()

    