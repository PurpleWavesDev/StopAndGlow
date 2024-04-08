# Blender Stop Motion Virtual Production Extension
# Contributor(s): Kira Vogt, Iris Sipka
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
        "name": "Stop Motion VP",
        "description": "Control VP hardware and cameras, capture footage and load it into your scene.",
        "author": "Kira Vogt, Iris Sipka",
        "version": (0, 1, 0),
        "blender": (4, 0, 0),
        "location": "3D View > Sidebar > Stop Motion VP Panel",
        "warning": "", # used for warning icon and text in add-ons panel
        "wiki_url": "",
        "tracker_url": "",
        "support": "COMMUNITY",
        "category": "Render"
        }

import bpy
import sys
import os.path as path

# Add parent path as module path
parent_module_path = path.abspath("..")
if not parent_module_path in sys.path:
    sys.path.append(parent_module_path)
    

def checkDependencies():
    # Check dependencies and install if needed
    import pip
    try:
        import zmq
    except:
        pip.main(['install', 'pyzmq', '--user'])



def register():
    checkDependencies()
    
    from . import properties, client, domectl, canvas, camera, scene, ui
    properties.register()
    client.register()
    domectl.register()
    canvas.register()
    camera.register()
    scene.register()
    ui.register()

def unregister():
    from . import properties, client, domectl, canvas, camera, scene, ui
    ui.unregister()
    scene.unregister()
    camera.unregister()
    canvas.unregister()
    domectl.unregister()
    client.unregister()
    properties.unregister()


if __name__ == '__main__':
    register()
    