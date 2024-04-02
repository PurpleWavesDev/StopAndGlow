from enum import StrEnum

# Chaining syntax:
# domectl --calibration /path/to/cal --config other/path --capture lights --process rti setting=something --view rti
# domectl --lights on --sleep 10 

class Commands(StrEnum):
    Config = '--config'
    Calibration = '--calibration'
    Capture = '--capture'
    Preview = '--preview'
    Load = '--load'
    LoadHdri = '--load_hdri'
    Convert = '--convert'
    Process = '--process'
    Render = '--render'
    View = '--view'
    Save = '--save'
    Send = '--send'
    Lights = '--lights'
    Sleep = '--sleep'
    Quit = '--quit'