from .rti import *
from .neural import *

from .exposureblend import *
from .rgbstack import *
from .lightstack import *
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
algorithms = {
    # Fitter algorithms with BSDF
    'ptm':     ('Polynominal Texture Mapping 3',    RtiProcessor,   {'fitter': PolyFitter.__name__, 'coordinate_system': CoordSys.LatLong.name, 'degree': 3, 'bsdf': 'ptm'}),
    'ptm4':    ('Polynominal Texture Mapping 4',    RtiProcessor,   {'fitter': PolyFitter.__name__, 'coordinate_system': CoordSys.LatLong.name, 'degree': 4, 'bsdf': 'ptm'}),
    'ptm5':    ('Polynominal Texture Mapping 5',    RtiProcessor,   {'fitter': PolyFitter.__name__, 'coordinate_system': CoordSys.LatLong.name, 'degree': 5, 'bsdf': 'ptm'}),
    'ptmz':    ('PTM Z-Vec Coordinates 3',          RtiProcessor,   {'fitter': PolyFitter.__name__, 'coordinate_system': CoordSys.ZVec.name,    'degree': 3, 'bsdf': 'ptmz'}),
    'ptmz4':   ('PTM Z-Vec Coordinates 4',          RtiProcessor,   {'fitter': PolyFitter.__name__, 'coordinate_system': CoordSys.ZVec.name,    'degree': 4, 'bsdf': 'ptmz'}),
    'ptmz5':   ('PTM Z-Vec Coordinates 5',          RtiProcessor,   {'fitter': PolyFitter.__name__, 'coordinate_system': CoordSys.ZVec.name,    'degree': 5, 'bsdf': 'ptmz'}),
    'shm':     ('Spherical Harmonics Mapping 1',    RtiProcessor,   {'fitter': SHFitter.__name__,   'coordinate_system': CoordSys.ZVec.name,    'degree': 1, 'bsdf': 'shm'}),
    'shm2':    ('Spherical Harmonics Mapping 2',    RtiProcessor,   {'fitter': SHFitter.__name__,   'coordinate_system': CoordSys.ZVec.name,    'degree': 2, 'bsdf': 'shm'}),
    'shm3':    ('Spherical Harmonics Mapping 3',    RtiProcessor,   {'fitter': SHFitter.__name__,   'coordinate_system': CoordSys.ZVec.name,    'degree': 3, 'bsdf': 'shm'}),
    'shm4':    ('Spherical Harmonics Mapping 4',    RtiProcessor,   {'fitter': SHFitter.__name__,   'coordinate_system': CoordSys.ZVec.name,    'degree': 4, 'bsdf': 'shm'}),
    'shm5':    ('Spherical Harmonics Mapping 5',    RtiProcessor,   {'fitter': SHFitter.__name__,   'coordinate_system': CoordSys.ZVec.name,    'degree': 5, 'bsdf': 'shm'}),
    'nrti':    ('Neural RTI',                       NeuralRti,      {'bsdf': 'nrti'}),
    'nrti3d':  ('Neural RTI 3D',                    NeuralRti,      {'bsdf': 'nrti'}),
    'blend':   ('Light Blending',                   None,           {'bsdf': 'blend'}),
}

generators = {
    # Generators without BSDF
    'normal':       ('Normal generator',            RtiProcessor,           {'fitter': NormalFitter.__name__}),
    'alpha':        ('Alpha Mask Generator',        LightstackProcessor,    {'mode': 'alpha'}),
    'alphadepth':   ('Alpha from Depth Generator',  DepthEstimator,         {'threshold': 0.3}),#TODO
    'depth':        ('Depth Estimator',             DepthEstimator,         {}),
}
