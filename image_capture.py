# DMX and Camera (gphoto2) interfaces

# Imports
import os
import sys
import logging
#import locale
#import subprocess

# DMX imports
from dmx import DMXInterface, DMXUniverse
from dmx.constants import DMX_MAX_ADDRESS
from typing import List

# Camera imports
import gphoto2 as gp
import rawpy
import imageio

def light():
    # Open an interface
    with DMXInterface("FT232R") as interface:
        # Create a universe
        universe = DMXUniverse()

        # New black frame
        frame = [0] * DMX_MAX_ADDRESS

        # Set values
        frame[132] = 50

        # Set frame and send update
        interface.set_frame(frame)
        interface.send_update()


def capture():
    camera = gp.Camera()
    camera.init()

    # Open an interface
    with DMXInterface("FT232R") as interface:
        # Create a universe
        universe = DMXUniverse()

        time_begin = time.time()
        print('Capturing image')
        for i in range (10,240):
            # Set light on
            frame = [0] * DMX_MAX_ADDRESS
            frame[i] = 255
            interface.set_frame(frame)
            interface.send_update()

            # Capture image
            file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
            print('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
            target = os.path.join('/tmp', file_path.name)
            print(i)
            #print('Copying image to', target)
            #camera_file = camera.file_get(
            #    file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
            #camera_file.save(target)

    print(f"Zeit: {time.time()-time_begin}")

    # Convert and save image
    raw = rawpy.imread(target)
    params=rawpy.Params(output_color=rawpy.ColorSpace.sRGB, noise_thr=20)
    rgb = raw.postprocess(params)
    imageio.imsave('default.png', rgb)
    #subprocess.call(['xdg-open', target])
    camera.exit()

