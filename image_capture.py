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

# Abseil flags
from absl import app
from absl import flags

# Types
HW = namedtuple("HW", ["cam", "lights"])

# Globals
FLAGS = flags.FLAGS
DATA_BASE_PATH='../HdM_BA/data'

# Global flag defines
flags.DEFINE_enum('mode', 'capture', ['capture', 'capture_quick', 'calibrate', 'calibrate_quick', 'download'], 'What the script should do.')
flags.DEFINE_enum('loglevel', 'INFO', ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], 'Level of logging.')
flags.DEFINE_string('img_output_path', '../HdM_BA/data', 'Where the image data should be written to.')
flags.DEFINE_string('download_name', 'download', 'Sequence name for downloads.')
flags.DEFINE_integer('download_offset', 1, 'Frame count starting from this number', lower_bound=0)
flags.DEFINE_boolean('delete_img', False, 'Delete captured images after download.')

#flags.DEFINE_integer('age', None, 'Your age in years.', lower_bound=0)

def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')

    # Prepare for tasks
    hw = HW(Cam(), Lights())

    # Execute task for requested mode
    if FLAGS.mode == 'calibrate':
        calibrate(hw)
    elif FLAGS.mode == 'download':
        download(hw, FLAGS.download_name, download_all=True)

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

    worker = CalWorker(hw, 0, 512)
    t = Timer(worker)

    t.start(0)
    t.join()

    download(hw, 'calibration')


def download(hw, name, download_all=False):
    log.info(f"Downloading sequence '{name}' to {FLAGS.img_output_path} (deletion is {FLAGS.delete_img})")
    if download_all:
        # Search for files on camera
        hw.cam.add_files(hw.cam.list_files(), FLAGS.download_offset)
    hw.cam.download(FLAGS.img_output_path, name, delete=FLAGS.delete_img)


if __name__ == '__main__':
    app.run(main)
