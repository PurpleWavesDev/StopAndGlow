import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from smvp_ipc import *

from . import properties as props
from . import client


# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------



# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

