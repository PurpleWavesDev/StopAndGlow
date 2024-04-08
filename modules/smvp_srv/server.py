import time
import zmq
import logging as log

from smvp_ipc import *

from .processing_queue import *
from .commands import *
from .render import bsdf
from .utils.utils import GetDatetimeNow


def run(port=9271):
    # Receiver socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")

    try:
        execute(socket, port, context)
    except Exception as e:
        send(socket, Message(Command.CommandDisconnect, {'message': f"Error: {str(e)}"}))
        

def execute(socket, port, context):
    remote_address = ""
    initalized = False
    queue = ProcessingQueue(context)
    while True:
        #  Wait for next request from client
        message = receive(socket)
        if message is None:
            print("Error receiving data")
            break
        
        if (not initalized) and message.command != Command.Init and message.command != Command.Ping:
            send(socket, Message(Command.CommandError, {'message': "Not initialized"}))
        
        # Match command
        match message.command:
            case Command.Ping:
                # Send pong
                send(socket, Message(Command.Pong, message.data))
            case Command.Pong:
                pass

            case Command.Init:
                remote_address = GetSetting(message.data, 'address', 'localhost')
                log.info(f"Server: Initializing for {remote_address}")
                if not initalized:
                    # Launch queue worker, this will initialize the hardware
                    queue.launch()
                    initalized = True
                send(socket, Message(Command.CommandOkay))
            
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
            case Command.CaptureLights | Command.CaptureBaked:
                name = GetSetting(message.data, 'name', GetDatetimeNow(), default_for_empty=True)
                root = queue.getConfig()['seq_folder']
                path = os.path.join(root, name)
                queue.putCommand(Commands.Capture, 'lights' if Command.CaptureLights else 'baked', {'name': name, 'discard_video': True}) # TODO: Implement discard_video
                #queue.putCommand(Commands.Save, path)
                send(socket, Message(Command.CommandProcessing, {'path': path}))
            ## Load from disk
            case Command.LoadFootage:
                # TODO: Check if path is valid
                queue.putCommand(Commands.Load, message.data['path'])
                send(socket, Message(Command.CommandOkay))
            
            
            ## LightInfo
            case Command.LightsSet:
                # Reset light data
                queue.putCommand(Commands.Render, 'reset')
                # Add each light separately
                for light in message.data:
                    queue.putCommand(Commands.Render, 'light', light)
                send(socket, Message(Command.CommandOkay))
                
            #case Command.LightsHdriRotation:
            #case Command.LightsHdriTexture:
            
            
            ## Preview
            # TODO: Join Request commands
            case Command.ReqPreview:
                # Send preview image
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', {'id': message.data['id'], 'mode': 'preview'})
                send(socket, Message(Command.CommandProcessing))
                # Generate alpha and send again
                queue.putCommand(Commands.Process, 'depth', {'target': 'preview', 'destination': 'alpha', 'rgb': False})
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', {'id': message.data['id'], 'mode': 'preview'})

            case Command.ReqRender:
                queue.putCommand(Commands.Render, 'render')
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', {'id': message.data['id'], 'mode': 'render'})
                send(socket, Message(Command.CommandProcessing))
                
            case Command.ReqBaked:
                # Capture and send
                queue.putCommand(Commands.Capture, 'baked')
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', {'id': message.data['id'], 'mode': 'baked'})
                send(socket, Message(Command.CommandProcessing))
                # Generate alpha and send again
                queue.putCommand(Commands.Process, 'depth', {'target': 'baked', 'destination': 'alpha', 'rgb': False})
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', {'id': message.data['id'], 'mode': 'baked'})
            
            case Command.ReqLive:
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', {'id': message.data['id'], 'mode': 'live'})
                send(socket, Message(Command.CommandProcessing))
            
            
            ## Render Algorithmns
            case Command.GetRenderAlgorithms:
                answer = {'algorithms': [(name, name_long) for name, name_long, _ in bsdfs]}
                send(socket, Message(Command.CommandAnswer, answer))
            
            case Command.GetRenderSettings:
                # TODO: Get renderer
                if renderer is not None:
                    answer = renderer.getDefaultSettings()
                    send(socket, Message(Command.CommandAnswer, answer))
                else:
                    send(socket, Message(Command.CommandError, {'message': 'No renderer selected'}))
            
            case Command.SetRenderer:
                algorithm = message.data['algorithm']
                try:
                    [None for name, _, _ in bsdfs if name == algorithm][0]
                    queue.putCommand(Commands.Render, 'config', message.data)
                    send(socket, Message(Command.CommandOkay))
                except:
                    send(socket, Message(Command.CommandError, {'message': 'Unknwon render algorithm selected'}))

                
            ## Live Viewer
            case Command.ViewerLaunch:    
                
                send(socket, Message(Command.CommandAnswer, answer))
            
            ## Camera settings
            #case Command.CameraSettings:
            #case Command.CameraPosition:
            
            case _:
                send(socket, Message(Command.CommandError, {"message": "Unknown command"}))
            
