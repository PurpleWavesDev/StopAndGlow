import time
import zmq

from smvp_ipc import *

from .processing_queue import *
from .commands import *


def run(port=9271):
    # Receiver socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")
    
    initalized = False
    queue = ProcessingQueue()

    while True:
        #  Wait for next request from client
        message = receive(socket)
        if message is None:
            print("Error receiving data")
            break
        
        if (not initalized) and message.command != Command.Init:
            send(socket, Message(Command.CommandError, {'message': "Not initialized"}))
        
        # Match command
        match message.command:
            case Command.Init:
                if not initalized:
                    # Launch queue worker, this will initialize the hardware
                    queue.launch()
                    initalized = True
                send(socket, Message(Command.CommandOkay))

            case Command.Ping:
                # Send pong
                send(socket, Message(Command.Pong, message.data))
            case Command.Pong:
                pass
            
            ## LightCtl commands
            case Command.LightCtlRand:
                #message.data # TODO
                queue.putCommand(Commands.Lights, 'on')
                send(socket, Message(Command.CommandOkay))
            case Command.LightCtlTop:
                queue.putCommand(Commands.Lights, 'top')
                send(socket, Message(Command.CommandOkay))
            case Command.LightCtlOff:
                queue.putCommand(Commands.Lights, 'off')
                send(socket, Message(Command.CommandOkay))
            
            ## Live Viewer
            #case Command.ViewerOpen:
                
            #case Command.ViewerClose:

            ## Preview
            case Command.Preview:
                send(socket, Message(Command.CommandProcessing))
            
            case Command.PreviewLive:
                # TODO: Localhost should be address of received message
                queue.putCommand(Commands.Send, f'localhost:{port+1}', {'id': message.data['id'], 'mode': 'live'})
                send(socket, Message(Command.CommandProcessing))
                
            case Command.PreviewHdri:
                send(socket, Message(Command.CommandProcessing))
            
            case _:
                send(socket, Message(Command.CommandError, {"message": "Unknown command"}))
            
            # Config commands
            # Resolution, Paths, Cals, .. ??
            #case Command.ConfResolution:
            #case Command.ConfCapturePath:
            #case Command.ConfCalibrationFile:
            #case Command.ConfGetLights:
            #
            ## LightInfo
            #case Command.LightsUpdate:
            #case Command.LightsHdriRotation:
            #case Command.LightsHdriTexture:
            #
            ## Several viewer modes?
            #
            #
            ## Full resoultion footage
            #case Command.CaptureHdri:
            #case Command.CaptureLights:
            ## Load from disk
            #case Command.LoadFootage:
            #
            ## Render loaded footage
            #case Command.GetRenderAlgorithms:
            #case Command.GetRenderSettings:
            #case Command.SetRenderer:
            #case Command.Process:
            #case Command.Render:
            #
            ## Camera settings
            #case Command.CameraSettings:
            #case Command.CameraTracking:
