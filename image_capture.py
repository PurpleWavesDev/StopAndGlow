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

# Abseil flags
from absl import app
from absl import flags

# Types
HW = namedtuple("HW", ["cam", "lights"])

# Globals
FLAGS = flags.FLAGS
DATA_BASE_PATH='../HdM_BA/data'

# Global flag defines
flags.DEFINE_enum('mode', 'capture', ['capture', 'capture_quick', 'calibrate', 'calibrate_quick', 'download', 'eval_cal'], 'What the script should do.')
flags.DEFINE_enum('loglevel', 'INFO', ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], 'Level of logging.')
flags.DEFINE_string('output_path', '../HdM_BA/data', 'Where the image data should be written to.')
flags.DEFINE_string('sequence_name', '', 'Sequence name for downloads.')
flags.DEFINE_integer('sequence_start', 1, 'Frame count starting from this number', lower_bound=0)
flags.DEFINE_boolean('keep_sequence', False, 'Keep images on camera after downloading.')

#flags.DEFINE_integer('age', None, 'Your age in years.', lower_bound=0)

def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')

    # First check modes without hardware requirements
    if FLAGS.mode == 'eval_cal':
        eval_cal(os.path.join(FLAGS.output_path, "allon"), os.path.join(FLAGS.output_path, "calibration")) # TODO: Flags

    else:
        # Prepare for tasks
        hw = HW(Cam(), Lights())

        # Execute task for requested mode
        #if True:
        #    capture_all_on(hw)
        if FLAGS.mode == 'calibrate':
            calibrate(hw)
            name = "calibration" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            download(hw, name, keep=FLAGS.keep_sequence)
        elif FLAGS.mode == 'download':
            name = "download" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            download(hw, name, download_all=True, keep=FLAGS.keep_sequence)

def capture_all_on(hw):
    frame = [100] * hw.lights.DMX_MAX_ADDRESS
    hw.lights.setFrame(frame)
    hw.lights.write()

    # Trigger camera
    hw.cam.capture(0)
    hw.lights.off()

    # Download image
    download(hw, 'allon', keep=False)


def calibrate(hw):
    log.info("Starting calibration")
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


def download(hw, name, download_all=False, keep=False):
    log.info(f"Downloading sequence '{name}' to {FLAGS.output_path}")
    if download_all:
        # Search for files on camera
        hw.cam.add_files(hw.cam.list_files(), FLAGS.sequence_start)
    hw.cam.download(FLAGS.output_path, name, keep=keep)

def eval_cal(path_allon, path_sequence):
    # Load data
    img_allon = ImgData(path_allon)
    img_seq = ImgData(path_sequence)
    log.info(f"Processing calibration sequencee with {len(img_seq)} frames")

    eval=Eval()
    #eval.find_center(img_allon)
    
    # Loop for all calibration frames
    del_list = []
    for id, img in img_seq:
        if not eval.filter_blackframe(img, 0.9):
            # Process frame
            eval.find_reflection(img)
        else:
            log.debug(f"Found blackframe '{id}'")
            del_list.append(id)
        img.unload()
    # Delete blackframes
    for id in del_list:
        del img_seq[id]

    # Save config
    log.info(f"Saving config '{0}' with {len(img_seq)} valid entries")

if __name__ == '__main__':
    app.run(main)
