from .depthestim import *
from .exposureblend import *
from .rgbstack import *
from .rti import *
from .neural import *

# PTM: Polynominal Texture Mapping
# HSH: 
# Not implemented:
# DMD: Discrete modal decomposition, described in "Discrete Modal Decomposition for surface appearance modelling and rendering"
# PCA + RBF: Principal Component Analysis (PCA) + Radial Basis Function (RBF)
# YCC: Color model to be used by fitter instead of RGB (Also chroma subsampling for better performance would be possible)
# BILINEAR: Replaces RBF in the PCA/RBF/YCC algorithm
# L-PTM etc.: Only luminance channel is fitted with constant

# Configured fitter with corresponding BSDFs in render submodule
# Key, full name, class, settings
fitter = [
    ('ptm',     'Polynominal Texture Mapping',  RtiProcessor,   {'fitter': PolyFitter.__name__, 'order': 3}),
    ('hsh2',    'Hemispherical Harmonics',      RtiProcessor,   {}),
    ('hsh3',    'Hemispherical Harmonics',      RtiProcessor,   {}),
    ('nrti',    'Neural RTI',                   NeuralRti,      {}),
    ('nrti3d',  'Neural RTI 3D',                NeuralRti,      {}),
]
