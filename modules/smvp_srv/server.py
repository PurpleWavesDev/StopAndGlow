import time
import zmq

from smvp_ipc import *

from .hw import *
from .data import *
from .process import *



def run():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:9271")
    
    hw = None
    dome = None
    initalized = False

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
                    hw = HW(Cam(), Lights(), Calibration('../HdM_BA/data/calibration/lightdome.json')) # Calibration(os.path.join(FLAGS.cal_folder, FLAGS.cal_name)
                    dome = LightCtl(hw)
                    initalized = True
                send(socket, Message(Command.CommandOkay))

            case Command.Ping:
                # Send pong
                send(socket, Message(Command.Pong, message.data))
            case Command.Pong:
                pass
            
            ## LightCtl commands
            case Command.LightCtlRand:
                message.data
                dome.setNth(6, 50)
                send(socket, Message(Command.CommandOkay))
            case Command.LightCtlTop:
                dome.setTop(60, 50)
                send(socket, Message(Command.CommandOkay))
            case Command.LightCtlOff:
                hw.lights.off()
                send(socket, Message(Command.CommandOkay))
            
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
            ## LightInfo
            #case Command.LightsUpdate:
            #case Command.LightsHdriRotation:
            #case Command.LightsHdriTexture:
            #
            ## Several viewer modes?
            #
            ## Preview
            #case Command.PreviewLive:
            #case Command.PreviewHdri:
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
