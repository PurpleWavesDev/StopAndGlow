from enum import StrEnum

# Chaining syntax:
# domectl --calibration /path/to/cal --config other/path --capture lights --process rti setting=something --view rti
# domectl --lights on --sleep 10 

class Commands(StrEnum):
    Config = '--config'
    Calibration = '--calibration'
    Preview = '--preview'
    Capture = '--capture'
    Load = '--load'
    LoadHdri = '--load_hdri'
    Calibrate = '--calibrate'
    Process = '--process'
    Render = '--render'
    View = '--view'
    Save = '--save'
    Send = '--send'
    Lights = '--lights'
    Camera = '--camera'
    Sleep = '--sleep'
    Quit = '--quit'
    LogLevel = '--loglevel'
    