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
    queue = ProcessingQueue(context)
    
    try:
        execute(socket, port, queue)
    except Exception as e:
        log.error(f"Uncaught exception: {str(e)}")
        send(socket, Message(Command.CommandDisconnect, {'message': f"Error: {str(e)}"}))
    
    # Clean up: Stop process and close socket
    queue.quit()
    context.destroy()

def execute(socket, port, queue):
    remote_address = ""
    initalized = False
    
    log.info(f"Server ready and listening on port {port}")
    while True:
        #  Wait for next request from client
        message = receive(socket)
        if message is None:
            log.error("Error receiving data")
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
                #queue.putCommand(Commands.Save, path) # TODO!
                send(socket, Message(Command.CommandProcessing, {'path': path}))
            ## Load from disk
            case Command.LoadFootage:
                # TODO: Check if path is valid
                queue.putCommand(Commands.Load, message.data['path'])
                
                # If depth map is not available, generate and save
                queue.putCommand(Commands.If, 'empty', {'data': 'depth'})
                queue.putCommand(Commands.Process, 'depth', {'target': 'preview', 'destination': 'data', 'rgb': False, 'override': False}) # destination: alpha
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', message.data)
                queue.putCommand(Commands.Save, 'data')
                queue.putCommand(Commands.EndIf, 'empty')

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
            case Command.RequestSequence:
                # id, mode, path in data
                # Load sequence
                queue.putCommand(Commands.Load, message.data['path'])
                
                if message.data['mode'] == 'render':
                    # Start rendering
                    queue.putCommand(Commands.Render, 'render')
                
                # Queue sending image and answer
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', message.data)                
                send(socket, Message(Command.CommandProcessing))
            
            case Command.RequestCamera:
                # id, mode in data
                # Capture and send
                if message.data['mode'] == 'baked':
                    queue.putCommand(Commands.Capture, 'baked')
                else:
                    queue.putCommand(Commands.Preview, 'live')
                queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', message.data)
                send(socket, Message(Command.CommandProcessing))
            
            
            ## Render Algorithmns
            case Command.GetRenderAlgorithms:
                answer = {'algorithms': [(name, name_long) for name, name_long, _ in bsdfs]}
                send(socket, Message(Command.CommandAnswer, answer))
            
            case Command.GetRenderSettings:
                algorithm = message.data['algorithm']
                try:
                    [None for _, _, bsdf in bsdfs if name == algorithm][0]
                    answer = bsdf.getDefaultSettings()
                    send(socket, Message(Command.CommandAnswer, answer))
                except:
                    send(socket, Message(Command.CommandError, {'message': 'No renderer selected'}))
            
            case Command.SetRenderer:
                algorithm = message.data['algorithm']
                try:
                    [None for name, _, _ in bsdfs if name == algorithm][0]
                    queue.putCommand(Commands.Render, 'config', message.data)
                    # TODO: Generate render data if not available
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
            
