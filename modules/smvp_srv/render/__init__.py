from .renderer import *
# BSDFs
from .lightstack import *
from .ptm import *
from .neural import *

# Key, full name, class, settings
bsdfs = {
    'ptm':     ('Polynominal Texture Mapping',  PtmBsdf,        {}),
    'hsh2':    ('Hemispherical Harmonics 2',    PtmBsdf,        {}),
    'hsh3':    ('Hemispherical Harmonics 3',    PtmBsdf,        {}),
    'nrti':    ('Neural RTI',                   NeuralRtiBsdf,  {}),
    'nrti3d':  ('Neural RTI 3D',                NeuralRtiBsdf,  {}),
    'stack':   ('Light Stack',                  LightstackBsdf, {}),
}
