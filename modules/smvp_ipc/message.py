from enum import Enum

    
class Command(Enum):
    # General commands
    Ping = 1
    Pong = 2
    Init = 3
    #State = 4

    # Command answers
    CommandOkay = 11
    CommandAnswer = 12
    CommandProcessing = 13
    CommandProgress = 14
    CommandComplete = 15
    CommandError = 16
    RecvOkay = 16
    RecvStop = 16
    RecvError = 16
    
    # Config commands
    # Resolution, Paths, Cals, .. ??
    ConfResolution = 21
    ConfCapturePath = 22
    ConfCalibrationFile = 23
    
    # LightCtl
    LightCtlTop = 41
    LightCtlRing = 42
    LightCtlRand = 43
    LightCtlOff = 44
    
    # Image data (capture & load)
    CaptureLights = 71
    CaptureBaked = 72
    LoadFootage = 75
    
    # LightInfo
    LightsSet = 31 # ??
    LightsUpdate = 32
    LightsHdriRotation = 35
    LightsHdriTexture = 36
    
    # Image requests
    ReqPreview = 61
    ReqBaked = 62
    ReqRender = 63
    ReqLive = 64
    ReqStop = 65
    
    # Render Algorithmns
    GetRenderAlgorithms = 81
    GetRenderSettings = 82
    SetRenderer = 83
    
    # Live Viewer
    ViewerLaunch = 51
    
    # Camera settings
    CameraSettings = 91
    CameraPosition = 92
    
    
class Message:
    command: Command
    data: dict
    
    def __init__(self, command, data = {}):
        self.command = command
        self.data = data
    
    def LightCtlMsg(command, brightness=100, ratio=0.25):
        return Message(command, {'brightness': brightness, 'ratio': ratio})
