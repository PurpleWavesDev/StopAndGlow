from .camera import *
from .config_canon90d import *

class CamOp:
    def FindMaxExposure(cam: Cam):
        # Get current exposure value
        exposure = cam.getExposure()
        index = list(CamConfigExposure.values()).index(exposure)

        cam.setExposure(list(CamConfigExposure.values())[index+1])
        exposure = cam.getExposure()
        return exposure
                
