# Blender Add-on Template
# Contributor(s): Aaron Powell (aaron@lunadigital.tv)
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
        "wiki_url": "https://blender.org",
        "tracker_url": "http://my.bugtracker.url",
        "support": "COMMUNITY",
        "category": "Render"
        }

import bpy

from . import properties
from . import client
from . import canvas
from . import ui

#
# Add additional functions here
#

def register():
    properties.register()
    client.register()
    canvas.register()
    ui.register()

def unregister():
    properties.unregister()
    client.unregister()
    canvas.unregister()
    ui.unregister()

if __name__ == '__main__':
    register()
