from ..hw.camera import *
# TODO: Config depending on camera model
from ..hw.camconf_canon90d import *

def FindMaxExposure(cam: Cam):
    # Get current exposure value
    exposure = cam.getExposure()
    index = list(CamConfigExposure.values()).index(exposure)
    
    cam.setExposure(list(CamConfigExposure.values())[index+1])
    exposure = cam.getExposure()
    return exposure
                
