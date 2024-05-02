from .renderer import *
# BSDFs
from .lightstack import * # TODO: Rename to lightblend?
from .ptm import *
from .neural import *
class ShmBsdf: # TODO
    pass

# key to bsdf class
bsdfs = {
    'ptm':     (PtmBsdf, {'coordinate_system': CoordSys.LatLong}),
    'ptmz':    (PtmBsdf, {'coordinate_system': CoordSys.ZVec}),
    'shm':     (ShmBsdf, {}),
    'nrti':    (NeuralRtiBsdf, {}),
    'blend':   (LightstackBsdf, {}),
}
