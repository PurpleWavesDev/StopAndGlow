# Imports
import sys
import os
import io
import time
from collections import namedtuple

import logging as log
from importlib import reload
#import threading
#import subprocess
#import locale

# DMX, Timer and Camera interfaces
from src.camera import Cam
from src.timer import Timer, Worker
from src.lights import Lights
from src.imgdata import *
from src.eval import Eval
from src.config import Config

# Abseil flags
from absl import app
from absl import flags

# Types
HW = namedtuple("HW", ["cam", "lights", "config"])

# Globals
FLAGS = flags.FLAGS
DATA_BASE_PATH='../HdM_BA/data'

# Global flag defines
# Mode and logging
flags.DEFINE_enum('mode', 'capture', ['capture', 'capture_quick', 'calibrate', 'calibrate_quick', 'download', 'eval_cal', 'debug_lightrun'], 'What the script should do.')
flags.DEFINE_enum('loglevel', 'INFO', ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], 'Level of logging.')
# Configuration
flags.DEFINE_string('config_path', '../HdM_BA/data/config', 'Where the configurations should be stored.')
flags.DEFINE_string('config_name', 'lightdome.json', 'Name of config file.')
flags.DEFINE_string('lights_config_name', '', 'Name of config to read available light addresses from.') # available_lights.json
# Sequence 
flags.DEFINE_string('output_path', '../HdM_BA/data', 'Where the image data should be written to.')
flags.DEFINE_string('sequence_name', '', 'Sequence name to download and/or evaluate.')
flags.DEFINE_string('mask_name', 'allon', 'Sequence name for the mask data.')
flags.DEFINE_integer('sequence_start', 1, 'Frame count starting from this number for downloads', lower_bound=0)
flags.DEFINE_boolean('keep_sequence', False, 'Keep images on camera after downloading.')

#flags.DEFINE_integer('age', None, 'Your age in years.', lower_bound=0)

def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')

    # First check modes without hardware requirements
    if FLAGS.mode == 'eval_cal':
        eval_cal(os.path.join(FLAGS.output_path, FLAGS.mask_name), os.path.join(FLAGS.output_path, FLAGS.sequence_name)) # TODO: Flags

    else:
        # Prepare for tasks
        #hw = HW(None, Lights(), Config(os.path.join(FLAGS.config_path, FLAGS.config_name)))
        hw = HW(Cam(), Lights(), Config(os.path.join(FLAGS.config_path, FLAGS.config_name)))

        # Execute task for requested mode
        #if True:
        #    capture_all_on(hw)
        if FLAGS.mode == 'capture':
            capture(hw)
            name = "capture" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            download(hw, name, keep=FLAGS.keep_sequence)
        elif FLAGS.mode == 'capture_quick':
            capture_quick(hw)
            #name = "capture" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            #download(hw, name, keep=FLAGS.keep_sequence)
        elif FLAGS.mode == 'calibrate':
            #calibrate(hw)
            capture_all_on(hw)
            capture(hw)
            name = "calibration" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            download(hw, name, keep=FLAGS.keep_sequence)
        elif FLAGS.mode == 'download':
            name = "download" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            download(hw, name, download_all=True, keep=FLAGS.keep_sequence)
        elif FLAGS.mode == 'debug_lightrun':
            debug_lightrun(hw)


#################### CAPTURE MODES ####################

def capture(hw):
    log.info("Starting capturing")
    # Worker class
    class CaptureWorker(Worker):
        def __init__(self, hw):
            self.hw=hw
            self.lights=self.hw.config.get()
            self.i=0

        def work(self) -> bool:
            # Set values
            light_id = self.lights[self.i]['id']
            self.hw.lights.setList([light_id])
            self.hw.lights.write()

             # Trigger camera
            self.hw.cam.capture(light_id)

            # Abort condition
            self.i+=1
            return self.i < len(self.lights)

    worker = CaptureWorker(hw)
    t = Timer(worker)
    t.start(0)
    t.join()

def capture_quick(hw):
    log.info("Starting quick capture (video)")
    # Worker class
    class CaptureWorker(Worker):
        def __init__(self, hw):
            self.hw=hw
            self.lights=self.hw.config.get()
            self.i=0
            self.blackframe=False

        def work(self) -> bool:
            if not self.blackframe:
                # Set values
                light_id = self.lights[self.i]['id']
                self.hw.lights.setList([light_id])
                self.hw.lights.write()
                self.blackframe=True

                # Trigger camera
                #self.hw.cam.capture(light_id)
                return True

            else:
                self.hw.lights.off()
                self.blackframe=False
                # Abort condition
                self.i+=1
                return self.i < len(self.lights)

    time.sleep(10)
    worker = CaptureWorker(hw)
    t = Timer(worker)
    hw.lights.off()
    time.sleep(1)
    # All on
    frame = [60] * hw.lights.DMX_MAX_ADDRESS
    hw.lights.setFrame(frame)
    hw.lights.write()
    time.sleep(0.5)
    # And off again
    hw.lights.off()
    time.sleep(0.5)
    t.start(1/(29.97/2))
    t.join()

def capture_all_on(hw):
    frame = [100] * hw.lights.DMX_MAX_ADDRESS
    hw.lights.setFrame(frame)
    hw.lights.write()

    # Trigger camera
    hw.cam.capture(0)
    hw.lights.off()

    # Download image
    download(hw, 'allon', keep=False)


#################### CALIBRATE MODES ####################

def calibrate(hw):
    log.info("Starting image capture")
    # Worker class
    class CalWorker(Worker):
        def __init__(self, hw, range_start, range_end):
            self.cam=hw.cam
            self.lights=hw.lights
            self.i = range_start
            self.end = range_end

        def work(self) -> bool:
            # Set values
            self.lights.setList([self.i])
            self.lights.write()

            # Trigger camera
            self.cam.capture(self.i)

            # Abort condition
            self.i+=1
            if self.i >= self.end:
                return False
            return True

    worker = CalWorker(hw, 0, hw.lights.DMX_MAX_ADDRESS)
    t = Timer(worker)

    t.start(0)
    t.join()


#################### CAMERA SETTINGS & DOWNLOAD MODES ####################

def download(hw, name, download_all=False, keep=False):
    log.info(f"Downloading sequence '{name}' to {FLAGS.output_path}")
    if download_all:
        # Search for files on camera
        hw.cam.add_files(hw.cam.list_files(), FLAGS.sequence_start)
    hw.cam.download(FLAGS.output_path, name, keep=keep)


#################### EVAL MODES ####################

def eval_cal(path_allon, path_sequence):
    # Load data
    img_allon = ImgData(path_allon)
    img_seq = ImgData(path_sequence)
    log.info(f"Processing calibration sequencee with {len(img_seq)} frames")

    config=Config()
    eval=Eval()

    # Find center of chrome ball with allon frame
    #eval.find_center(img_allon.get(0))
    
    # Loop for all calibration frames
    del_list = []
    for id, img in img_seq:
        if not eval.filter_blackframe(img, 0.9):
            # Process frame
            eval.find_reflection(img)
            config.addLight(id, [0,0], [0,0])
        else:
            log.debug(f"Found blackframe '{id}'")
            del_list.append(id)
        img.unload()
    # Delete blackframes
    for id in del_list:
        del img_seq[id]

    # Save config
    log.info(f"Saving config to '{FLAGS.config_path}' with lights from ID {config.get_key_bounds()}")
    config.save(FLAGS.config_path, FLAGS.config_name)


#################### DEBUG MODES ####################

def debug_lightrun(hw):
    log.info("Starting lightrun")
    # Worker class
    class LightTest(Worker):
        def __init__(self, hw):
            self.hw=hw
            self.lights=self.hw.config.get()
            self.i=0

        def work(self) -> bool:
            # Set values
            self.hw.lights.setList([self.lights[self.i]['id']])
            self.hw.lights.write()

            # Abort condition
            self.i+=1
            return self.i < len(self.lights)


    log.info(f"Running through {len(hw.config)} lights with IDs {hw.config.get_key_bounds()}")
    worker = LightTest(hw)
    t = Timer(worker)
    t.start(1/15)
    t.join()

if __name__ == '__main__':
    app.run(main)
