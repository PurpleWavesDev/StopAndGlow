from enum import Enum

    
class Command(Enum):
    # General commands
    Init = 0
    Ping = 1
    Pong = 2
    Info = 3
    Err = 4
    Trace = 5
    # Command answers
    CommandOkay = 11
    CommandAnswer = 12
    CommandProcessing = 13
    CommandProgress = 14
    CommandComplete = 15
    CommandError = 16
    
    # Config commands
    # Resolution, Paths, Cals, .. ??
    ConfResolution = 21
    ConfCapturePath = 22
    ConfCalibrationFile = 23
    ConfGetLights = 26
    
    # LightInfo
    LightsSet = 31 # ??
    LightsUpdate = 32
    LightsHdriRotation = 35
    LightsHdriTexture = 36
    
    # LightCtl
    LightCtlTop = 41
    LightCtlRing = 42
    LightCtlRand = 43
    LightCtlOff = 44
    
    # Live Viewer
    ViewerOpen = 51
    ViewerClose = 52
    # Several viewer modes?
    
    #
    Preview = 61
    PreviewBaked = 62
    PreviewLive = 63
    
    # Full resoultion footage
    CaptureLights = 71
    CaptureBaked = 72
    # Load from disk
    LoadFootage = 75
    
    # Render loaded footage
    GetRenderAlgorithms = 81
    GetRenderSettings = 82
    SetRenderer = 83
    Process = 84
    Render = 85
    
    # Camera settings
    CameraSettings = 91
    CameraTracking = 92
    
    
class Message:
    command: Command
    data: dict
    
    def __init__(self, command, data = {}):
        self.command = command
        self.data = data
    
    def LightCtlMsg(command, brightness=100, ratio=0.25):
        return Message(command, {'brightness': brightness, 'ratio': ratio})
