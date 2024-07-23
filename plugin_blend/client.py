import os
import time
import subprocess
from threading import Thread, Lock
import numpy as np
import queue
import socket
import zmq

import bpy
from bpy.types import WindowManager as wm

from sng_ipc import *

# Connection infos
context = None
send_sock = None
connected = False
server = None

# Receiver thread
receiver = None
receiver_lock = Lock()
receiver_queue = queue.Queue()

# Request data
image_requests = {}
request_count = 0

# Constants
SERVER_CWD = os.path.abspath("../../")
SERVER_COMMAND = [".venv/bin/python", "server.py"]
PING_INTERVAL = 10

# -------------------------------------------------------------------
# Launch, Connect, Send
# -------------------------------------------------------------------        
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
    send_sock.connect(server_address)
    # Set timeout and disconnect after timeout option
    send_sock.setsockopt(zmq.RCVTIMEO, 1000)
    send_sock.setsockopt(zmq.LINGER, 0)
    # Send an init message and wait for answer
    message = Message(Command.Init, {'address': getHostname()})
    try:
        connected = sendMessage(message, reconnect=False, force=True) is not None
        
        if connected:
            # Launch service, receiving port is server port +1
            receiver = Thread(target=serviceRun, args=(port+1, ))
            receiver.start()
            # Launch ping timer
            bpy.app.timers.register(ping, first_interval=PING_INTERVAL)
        
        return connected
    except Exception as e:
        print(f"SMVP Error: Can't connect to server {server_address} ({str(e)})")
    return False

def smvpDisconnect():
    global send_sock
    global connected
    global receiver
    
    # Unregister ping function
    if bpy.app.timers.is_registered(ping):
        bpy.app.timers.unregister(ping)

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
        bpy.ops.wm.sng_connect()
    if connected or force:
        # Send message
        try:
            ipc.send(send_sock, message)
            # Receive answer
            answer = ipc.receive(send_sock)
            if answer.command == Command.CommandError:
                # Print error message
                print("Received error from smvp server" + f": {answer.data['message']}" if 'message' in answer.data else "")
            elif answer.command == Command.CommandDisconnect:
                print("SMVP Server disconnected" + f": {answer.data['message']}" if 'message' in answer.data else "")
                smvpDisconnect()
            return answer
        except Exception as err:
            print(f"SMVP Communication error: {str(err)}")
            smvpDisconnect()
    return None


# -------------------------------------------------------------------
# Service interface
# -------------------------------------------------------------------        
def serviceAddReq(image_name) -> int:
    global image_requests
    global request_count
    
    #serviceRemoveReq(image_name)
    id, _  = serviceGetReq(image_name)
    
    # Add new ID
    if id is None:
        id = request_count
        request_count += 1
    
    image_requests[id] = (image_name, False)
    return id

def serviceRemoveReq(image_name):
    global image_requests
    global request_count
    
    # Delete old entry
    old_ids = [id for id, data in image_requests.items() if data[0] == image_name]
    for id in old_ids:
        del image_requests[id]

def serviceGetReq(image_name):
    global image_requests
    global request_count
    
    # Get entry
    img_id = [(id, data[1]) for id, data in image_requests.items() if data[0] == image_name]
    if img_id:
        return img_id[0]
    return (None, False)

def serviceGetReceived(id) -> bool:
    global image_requests
    return image_requests[id][1]


# -------------------------------------------------------------------
# Service Function and Timer Callbacks
# -------------------------------------------------------------------        
def serviceRun(port):
    global connected
    global context
    global image_requests
    global receiver_lock 

    with receiver_lock: # TODO what is this used for?!
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
                    elif not image_requests[id][0] in bpy.data.images:
                        # Image missing
                        ipc.send(recv_sock, Message(Command.RecvStop))
                        print(f"SMVP receiver warning: Image {image_requests[id][0]} not found")
                    else:
                        ipc.send(recv_sock, Message(Command.RecvOkay))
                        # Add data to queue and launch timer to apply on main thread
                        receiver_queue.put((id, np.flipud(img_data).flatten()))
                        if not bpy.app.timers.is_registered(serviceApply):
                            bpy.app.timers.register(serviceApply)
                except Exception as e:
                    # Send error
                    ipc.send(recv_sock, Message(Command.RecvError, {'message': str(e)}))
                    print(f"SMVP receiver error: Can't read received data ({str(e)})")
    
        # Clean up connection
        recv_sock.close()


def serviceApply():
    global image_requests
    
    while not receiver_queue.empty():
        id, pix_data = receiver_queue.get()
        # In case ID got removed before timer can access it
        if id in image_requests:
            # Update image
            bpy.data.images[image_requests[id][0]].pixels.foreach_set(pix_data)
            # Set update flag and mark as received
            bpy.data.images[image_requests[id][0]].update_tag()
            image_requests[id] = (image_requests[id][0], True)
        
    return None


def ping():
    global connected
    global send_sock
    
    if connected:
        try:
            ipc.send(send_sock, Message(Command.Ping))
            answer = ipc.receive(send_sock)
            if answer.command == Command.Pong:
                # Answer received, call function after interval
                return PING_INTERVAL
            else:
                print(f"Unexpected answer '{answer.command.name}' for ping command")
                smvpDisconnect()
        except Exception as e:
            print(f"Ping error ({str(e)}), disconnecting SL server")
            smvpDisconnect()
    # Stop timer
    return None


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------        
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

    