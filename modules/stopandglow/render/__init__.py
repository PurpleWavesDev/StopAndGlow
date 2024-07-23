from .renderer import *
# BSDFs
from .lightblend import *
from .ptm import *
from .shm import *
from .neural import *

# key to bsdf class
bsdfs = {
    'ptm':     (PtmBsdf, {'coordinate_system': CoordSys.LatLong}),
    'ptmz':    (PtmBsdf, {'coordinate_system': CoordSys.ZVec}),
    'shm':     (ShmBsdf, {}),
    'nrti':    (NeuralRtiBsdf, {}),
    'blend':   (LightblendBsdf, {}),
}
