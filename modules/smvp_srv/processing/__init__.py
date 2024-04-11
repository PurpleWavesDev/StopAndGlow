from .exposureblend import *
from .rgbstack import *

from .rti import *
from .neural import *
from .depthestim import *

# PTM: Polynominal Texture Mapping
# HSH: Hemispherical harmonics, kind off Fourier Transformations mapped to a Hemisphere. Spherical Harmonics might be better suited?!
# Not implemented:
# DMD: Discrete modal decomposition, described in "Discrete Modal Decomposition for surface appearance modelling and rendering"
# PCA + RBF: Principal Component Analysis (PCA) + Radial Basis Function (RBF)
# YCC: Color model to be used by fitter instead of RGB (Also chroma subsampling for better performance would be possible)
# BILINEAR: Replaces RBF in the PCA/RBF/YCC algorithm
# L-PTM etc.: Only luminance channel is fitted with constant

# Configured fitter with corresponding BSDFs in render submodule
# Key, full name, class, settings
fitters = {
    'ptm':     ('Polynominal Texture Mapping',  RtiProcessor,   {'fitter': PolyFitter.__name__, 'order': 3}),
    'hsh2':    ('Hemispherical Harmonics',      RtiProcessor,   {}),
    'hsh3':    ('Hemispherical Harmonics',      RtiProcessor,   {}),
    'normal':  ('Normal fitter',                RtiProcessor,   {'fitter': NormalFitter.__name__}),
    'nrti':    ('Neural RTI',                   NeuralRti,      {}),
    'nrti3d':  ('Neural RTI 3D',                NeuralRti,      {}),
    'depth':   ('Depth Estimator',              DepthEstimator, {}),
}
