import time
import zmq

from smvp_ipc import *

def run():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:9271")

    while True:
        #  Wait for next request from client
        message = receive(socket)
        if message is None:
            print("Error receiving data")
            break
        
        match message.command:
            case Command.Init:
                send(socket, Message(Command.CommandOkay))
            case Command.Ping:
                # Send pong
                send(socket, Message(Command.Pong, message.data))
            case Command.Pong:
                pass
            
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
            ## LightCtl
            #case Command.LightCtlRand:
            #case Command.LightCtlTop:
            #case Command.LightCtlOff:
            #
            ## Live Viewer
            #case Command.ViewerOpen:
            #case Command.ViewerClose:
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
