import time
import zmq
import logging as log
import pathlib

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
                # Create folder
                name = GetSetting(message.data, 'name', GetDatetimeNow(), default_for_empty=True)
                path = os.path.join(os.path.abspath(queue.getConfig()['seq_folder']), name)
                pathlib.Path(path).mkdir(parents=True, exist_ok=True)
                
                send(socket, Message(Command.CommandProcessing, {'path': path}))
                queue.putCommand(Commands.Capture, 'lights' if Command.CaptureLights else 'baked', {'name': name, 'discard_video': True}) # TODO: Implement discard_video
                queue.putCommand(Commands.Save, 'all')
                # Generate depth map
                queue.putCommand(Commands.Process, 'depth', {'target': 'preview', 'destination': 'data', 'rgb': False})
                queue.putCommand(Commands.Save, 'data')
            ## Load from disk
            case Command.LoadFootage:
                # Check if path is valid
                path = message.data['path']
                if os.path.exists(path):
                    send(socket, Message(Command.CommandOkay))
                    
                    queue.putCommand(Commands.Load, path)
                    #queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', message.data) # TODO
                    
                    # If depth map is not available, generate and save
                    queue.putCommand(Commands.If, 'empty', {'data': 'depth'})
                    queue.putCommand(Commands.Process, 'depth', {'target': 'preview', 'destination': 'data', 'rgb': False, 'override': False}) # destination: alpha
                    #queue.putCommand(Commands.Send, f'{remote_address}:{port+1}', message.data) # TODO
                    queue.putCommand(Commands.Save, 'data')
                    queue.putCommand(Commands.EndIf, 'empty')
                else:
                    send(socket, Message(Command.CommandError, {'message': "Path '{path}' doesn not exist"}))
            
            
            ## LightInfo
            case Command.LightsSet:
                # Clear light data
                queue.putCommand(Commands.Render, 'clear')
                # Add each light separately
                for light in message.data:
                    queue.putCommand(Commands.Render, 'light', light)
                send(socket, Message(Command.CommandOkay))
                
            case Command.LightsHdriRotation:
                queue.putCommand(Commands.Render, 'hdri_data') # TODO data missing
                queue.putCommand(Commands.Render, 'reset')
                send(socket, Message(Command.CommandOkay))

            case Command.LightsHdriTexture:
                path = message.data['path']
                if os.path.exists(path):
                    send(socket, Message(Command.CommandOkay)) 
                    queue.putCommand(Commands.LoadHdri, path)
                    queue.putCommand(Commands.Render, 'hdri')
                    queue.putCommand(Commands.Render, 'reset')
                    
                else:
                    # HDRI Path does not exist
                    send(socket, Message(Command.CommandError, {'message': "Path '{path}' doesn not exist"}))
            
            case Command.CanvasSet:
                # Hier kommen die transform daten an
                #message.data
                send(socket, Message(Command.CommandOkay))
            
            
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
                answer = {'algorithms': [(name, values[0]) for name, values in algorithms.items() if 'bsdf' in values[2]]}
                send(socket, Message(Command.CommandAnswer, answer))
            
            case Command.GetRenderSettings: # TODO: What settings should be exposed anyway?
                algo_key = message.data['algorithm']
                try:
                    name, algo_class, algo_settings = algorithms[algo_key]
                    answer = algo_class.getDefaultSettings()
                    send(socket, Message(Command.CommandAnswer, answer))
                except:
                    send(socket, Message(Command.CommandError, {'message': 'No valid algorithm specified'}))
            
            case Command.SetRenderer:
                algo_key = message.data['algorithm']
                if algo_key in algorithms:
                    send(socket, Message(Command.CommandOkay))
                    
                    # Generate algorithm data if needed
                    if algorithms[algo_key][1] is not None: # Processing class for algorithm exists
                        queue.putCommand(Commands.If, 'empty', {'data': algo_key})
                        queue.putCommand(Commands.Process, 'fitting', {'fitter': algo_key, 'target': 'sequence', 'destination': 'data'})
                        queue.putCommand(Commands.Save, 'data')
                        queue.putCommand(Commands.EndIf, 'empty')
                    # Also generate normal map
                    queue.putCommand(Commands.If, 'empty', {'data': 'normal'})
                    queue.putCommand(Commands.Process, 'generate', {'generator': 'normal', 'target': 'sequence', 'destination': 'data'})
                    queue.putCommand(Commands.Save, 'data')
                    queue.putCommand(Commands.EndIf, 'empty')
                    # Configure renderer
                    queue.putCommand(Commands.Render, 'config', message.data)
                    queue.putCommand(Commands.Render, 'init')
                else:
                    send(socket, Message(Command.CommandError, {'message': 'No valid algorithm specified'}))

                
            ## Live Viewer
            case Command.ViewerLaunch:    
                
                send(socket, Message(Command.CommandAnswer, answer))
            
            ## Camera settings
            #case Command.CameraSettings:
            #case Command.CameraPosition:
            
            case _:
                send(socket, Message(Command.CommandError, {"message": "Unknown command"}))
            
