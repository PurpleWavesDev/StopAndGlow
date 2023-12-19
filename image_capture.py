# DMX and Camera (gphoto2) interfaces

# Imports
import os
import sys
import io
import time
import logging
import threading
import subprocess
import signal
#import locale

# DMX imports
from dmx import DMXInterface, DMXUniverse
from dmx.constants import DMX_MAX_ADDRESS
from typing import List

# Camera imports
import gphoto2 as gp
import rawpy
import imageio
from PIL import Image

#kill gphoto2 process that occurs whenever connect camera
def killgphoto2():
    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out,err = p.communicate()
    for line in out.splitlines():
        if b'gvfsd-gphoto2' in line:
            #kill process
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)
   
killgphoto2()


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
            target = os.path.join('.tmp', file_path.name)
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

#capture()


def timer_fn(delay):
    next_call = time.time()
    i = 20
    while running:
        # Work
        # New black frame
        frame = [0] * DMX_MAX_ADDRESS

        # Set values
        frame[i] = 255
        i=(i+1)%512

        # Set frame and send update
        interface.set_frame(frame)
        interface.send_update()

        # Trigger camera
        #camera.trigger_capture()
        camera.capture(gp.GP_CAPTURE_IMAGE)

        # Capture image/preview
        #capture = camera.capture_preview()
        #filedata = capture.get_data_and_size()
        #data = memoryview(filedata)
        #image = Image.open(io.BytesIO(filedata))
        #image.save(f"test_{i}.png")

        # Sleep until next frame
        next_call = next_call+delay
        time_sleep = next_call - time.time()
        if time_sleep < 0:
            print(f"Error: Overrun timer by {abs(time_sleep)}")
            next_call = time.time()
        else:
            time.sleep(time_sleep)

running=True
interface = DMXInterface("FT232R")

camera = gp.Camera()
camera.init()
#camera.capture(gp.GP_CAPTURE_IMAGE)
#camera.trigger_capture()

timerThread = threading.Thread(target=timer_fn, args=(1,))
timerThread.start()

time.sleep(5)
running=False
timerThread.join()
#camera.trigger_capture()

