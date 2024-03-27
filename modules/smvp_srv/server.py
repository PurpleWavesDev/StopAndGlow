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
    renderer = None
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
            
            ## Config commands for resolution, paths, calibration
            case Command.ConfResolution:
                try:
                    res_x, res_y = message.data['resolution']
                    # Set resolution
                    
                    send(socket, Message(Command.CommandOkay))
                except:
                    send(socket, Message(Command.CommandError, {'message': 'Failed to parse resolution value'}))
            case Command.ConfCapturePath:
                capture_path = message.data['path']
                if os.path.isdir(capture_path):
                    # Set folder
                    
                    send(socket, Message(Command.CommandOkay))
                else:
                    send(socket, Message(Command.CommandError, {'message': 'Path is not a folder'}))
            case Command.ConfCalibrationFile:
                cal_file = message.data['path']
                if os.path.isfile(cal_file):
                    # Load cal file
                    
                    send(socket, Message(Command.CommandOkay))
                else:
                    send(socket, Message(Command.CommandError, {'message': 'Path is not a file'}))
            
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
            # TODO: Localhost should be address of received message
            case Command.ReqPreview:
                # Send preview image
                queue.putCommand(Commands.Send, f'localhost:{port+1}', {'id': message.data['id'], 'mode': 'preview'})
                send(socket, Message(Command.CommandProcessing))
                
            case Command.ReqBaked:
                queue.putCommand(Commands.Capture, 'hdri')
                queue.putCommand(Commands.Send, f'localhost:{port+1}', {'id': message.data['id'], 'mode': 'baked'})
                send(socket, Message(Command.CommandProcessing))
            
            case Command.ReqLive:
                queue.putCommand(Commands.Send, f'localhost:{port+1}', {'id': message.data['id'], 'mode': 'live'})
                send(socket, Message(Command.CommandProcessing))

            case Command.ReqRender:
                queue.putCommand(Commands.Send, f'localhost:{port+1}', {'id': message.data['id'], 'mode': 'render'})
                send(socket, Message(Command.CommandProcessing))

            
            ## LightInfo
            case Command.LightsSet:
                send(socket, Message(Command.CommandOkay))
                pass
                message.data['sun'] # Rotation, spread(?)
                message.data['point'] # Position, size(?)
                #message.data['spot'] # Position, rotation, angle, falloff(?), size(?)
                queue.putCommand(Commands.Lights)
            
            #case Command.LightsHdriRotation:
            #case Command.LightsHdriTexture:
            
            ## Render loaded footage
            case Command.GetRenderAlgorithms:
                answer = {'algorithms': [(rend.name_short, rend.name) for rend in renderers]}
                send(socket, Message(Command.CommandAnswer, answer))
            case Command.SetRenderer:
                rend_name = message.data['algorithm']
                try:
                    renderer = [rend for rend in renderers if rend.name_short == rend_name][0]
                except:
                    send(socket, Message(Command.CommandError, {'message': 'Unknwon render algorithm selected'}))
            case Command.GetRenderSettings:
                if renderer is not None:
                    answer = renderer.getDefaultSettings()
                    send(socket, Message(Command.CommandAnswer, answer))
                else:
                    send(socket, Message(Command.CommandError, {'message': 'No renderer selected'}))
            ##case Command.Process: # Implicitly called?
                
            ## Live Viewer
            #case Command.ViewerOpen:    
            #case Command.ViewerClose:
            
            ## Camera settings
            #case Command.CameraSettings:
            #case Command.CameraTracking:
            
            case _:
                send(socket, Message(Command.CommandError, {"message": "Unknown command"}))
            
