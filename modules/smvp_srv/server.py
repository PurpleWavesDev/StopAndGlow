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
            case Command.LightCtlTop:
                queue.putCommand(Commands.Lights, 'top', message.data)
                send(socket, Message(Command.CommandOkay))
            case Command.LightCtlRing:
                queue.putCommand(Commands.Lights, 'ring', message.data)
                send(socket, Message(Command.CommandOkay))
            case Command.LightCtlRand:
                queue.putCommand(Commands.Lights, 'rand', message.data)
                send(socket, Message(Command.CommandOkay))
            case Command.LightCtlOff:
                queue.putCommand(Commands.Lights, 'off')
                send(socket, Message(Command.CommandOkay))

            ## Full resoultion footage
            case Command.CaptureLights:
                queue.putCommand(Commands.Capture, 'lights')
                queue.putCommand(Commands.Save, '')
                send(socket, Message(Command.CommandOkay))
            case Command.CaptureBaked:
                queue.putCommand(Commands.Capture, 'hdri')
                queue.putCommand(Commands.Save, '')
                send(socket, Message(Command.CommandOkay))
            ## Load from disk
            case Command.LoadFootage:
                queue.putCommand(Commands.Load, message.data['path'])
                send(socket, Message(Command.CommandOkay))
            
            ## Preview
            case Command.Preview:
                queue.putCommand(Commands.Send, f'localhost:{port+1}', {'id': message.data['id'], 'mode': 'preview'})
                send(socket, Message(Command.CommandProcessing))
                
            case Command.PreviewBaked:
                queue.putCommand(Commands.Capture, 'hdri')
                queue.putCommand(Commands.Send, f'localhost:{port+1}', {'id': message.data['id'], 'mode': 'baked'})
                send(socket, Message(Command.CommandProcessing))
            
            case Command.PreviewLive:
                # TODO: Localhost should be address of received message
                queue.putCommand(Commands.Send, f'localhost:{port+1}', {'id': message.data['id'], 'mode': 'live'})
                send(socket, Message(Command.CommandProcessing))
            
            ## LightInfo
            case Command.LightsSet:
                pass
                message.data['directional'] # Rotation, spread(?)
                message.data['points'] # Position, size(?)
                message.data['spot'] # Position, rotation, angle, falloff(?), size(?)
                #queue.putCommand()
            
            #case Command.LightsHdriRotation:
            #case Command.LightsHdriTexture:
            
            ## Render loaded footage
            #case Command.GetRenderAlgorithms:
            #case Command.GetRenderSettings:
            #case Command.SetRenderer:
            #case Command.Process:
            #case Command.Render:
            
            ## Live Viewer
            #case Command.ViewerOpen:    
            #case Command.ViewerClose:
            
            case _:
                send(socket, Message(Command.CommandError, {"message": "Unknown command"}))
            
            
            
            # Config commands
            # Resolution, Paths, Cals, .. ??
            #case Command.ConfResolution:
            #case Command.ConfCapturePath:
            #case Command.ConfCalibrationFile:
            #case Command.ConfGetLights:
            #
            #
            ## Several viewer modes?
            #
            #
            #
            #
            ## Camera settings
            #case Command.CameraSettings:
            #case Command.CameraTracking:
