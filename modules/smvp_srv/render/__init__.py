from .renderer import *
# BSDFs
from .lightstack import *
from .rti_poly import *

# Key, full name, class, settings
bsdfs = [
    ('ptm',     'Polynominal Texture Mapping',  RTIPolyBsdf,    {}),
    ('hsh2',    'Hemispherical Harmonics',      RTIPolyBsdf,    {}),
    ('hsh3',    'Hemispherical Harmonics',      RTIPolyBsdf,    {}),
    ('nrti',    'Neural RTI',                   RTIPolyBsdf,    {}),
    ('nrti3d',  'Neural RTI 3D',                RTIPolyBsdf,    {}),
    ('stack',   'Light Stack',                  LightstackBsdf, {}),
]
