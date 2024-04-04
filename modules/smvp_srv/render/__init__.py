from .renderer import *
# BSDFs
from .lightstack import *
from .rti_poly import *

bsdfs = [('stack', 'Light Stack', LightstackBsdf), ('poly', 'RTI Polynominal', RTIPolyBsdf)]
