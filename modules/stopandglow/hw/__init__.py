# Sub-Module for hardware-related stuff

# Imports
from collections import namedtuple

from .camera import *
from .lights import *

# Types
HW = namedtuple("HW", ["cam", "lights"])
