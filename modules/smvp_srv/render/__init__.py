from .renderer import *
# BSDFs
from .lightstack import * # TODO: Rename to lightblend?
from .ptm import *
from .shm import *
from .neural import *

# key to bsdf class
bsdfs = {
    'ptm':     (PtmBsdf, {'coordinate_system': CoordSys.LatLong}),
    'ptmz':    (PtmBsdf, {'coordinate_system': CoordSys.ZVec}),
    'shm':     (ShmBsdf, {}),
    'nrti':    (NeuralRtiBsdf, {}),
    'blend':   (LightstackBsdf, {}),
}
