# Imports
import sys
import os
import io
import time
from collections import namedtuple
from importlib import reload

# Flags and logging
from absl import app
from absl import flags
import logging as log

# DMX, Config and Camera interfaces
from src.camera import Cam
from src.lights import Lights
from src.config import Config
# Timer and worker
from src.timer import Timer, Worker
import src.capture_worker as worker
# Image and dome data, evaluation
from src.imgdata import *
from src.lightdome import Lightdome
from src.eval import Eval
from src.rti import Rti


# Types
HW = namedtuple("HW", ["cam", "lights", "config"])

# Globals
FLAGS = flags.FLAGS
# TODO: Unify, input variable?
DATA_BASE_PATH='../HdM_BA/data'
NAME_MASK_EXT='_mask'

# Global flag defines
# Mode and logging
flags.DEFINE_enum('mode', 'capture', ['capture', 'capture_quick', 'calibrate', 'calibrate_quick', 'download', 'eval_cal', 'lights_top', 'lights_hdri', 'lights_run', 'debug'], 'What the script should do.')
flags.DEFINE_enum('loglevel', 'INFO', ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], 'Level of logging.')
# Configuration
flags.DEFINE_string('config_path', '../HdM_BA/data/config', 'Where the configurations should be stored.')
flags.DEFINE_string('config_name', 'lightdome.json', 'Name of config file.')
flags.DEFINE_string('lights_config_name', '', 'Name of config to read available light addresses from.') # available_lights.json
# Sequence 
flags.DEFINE_string('output_path', '../HdM_BA/data', 'Where the image data should be written to.')
flags.DEFINE_string('sequence_name', '', 'Sequence name to download and/or evaluate.')
#flags.DEFINE_string('mask_name', 'mask', 'Sequence name for the mask data.')
flags.DEFINE_integer('sequence_start', 1, 'Frame count starting from this number for downloads', lower_bound=0)
flags.DEFINE_boolean('keep_sequence', False, 'Keep images on camera after downloading.')
flags.DEFINE_integer('video_frames_skip', 1, 'Frames to skip between valid frames in video sequence', lower_bound=0)


def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')

    # First check modes without hardware requirements
    if FLAGS.mode == 'eval_cal':
        name = "calibration" if FLAGS.sequence_name == "" else FLAGS.sequence_name
        eval_cal(os.path.join(FLAGS.output_path, name))

    else:
        # Prepare for tasks
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
            name = "calibration" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            # Capture with all lights on for masking frame
            capture_all_on(hw)
            download(hw, name+NAME_MASK_EXT, keep=False)
            capture(hw)
            download(hw, name, keep=FLAGS.keep_sequence)
        elif FLAGS.mode == 'download':
            name = "download" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            download(hw, name, download_all=True, keep=FLAGS.keep_sequence)
        elif FLAGS.mode == 'lights_top':
            lights_top(hw)
        elif FLAGS.mode == 'lights_hdri':
            lights_hdri(hw)
        elif FLAGS.mode == 'lights_run':
            lights_run(hw)
        elif FLAGS.mode == 'debug':
            debug(hw)


#################### CAPTURE MODES ####################

def capture(hw):
    log.info("Starting image capture")
    t = Timer(worker.ImageCapture(hw), self.hw.config)
    t.start(0)
    t.join()

def capture_quick(hw):
    log.info("Starting quick capture (video)")
    # Worker class
    time.sleep(10)
    t = Timer(worker.VideoCapture(hw))
    hw.lights.off()
    time.sleep(1)
    # All on
    frame = [60] * Lights.DMX_MAX_ADDRESS
    hw.lights.setFrame(frame)
    hw.lights.write()
    time.sleep(0.5)
    # And off again
    hw.lights.off()
    time.sleep(0.5)
    t.start(1/(29.97/2))
    t.join()

def capture_all_on(hw):
    frame = [100] * Lights.DMX_MAX_ADDRESS
    hw.lights.setFrame(frame)
    hw.lights.write()

    # Trigger camera
    hw.cam.capturePhoto(0)
    hw.lights.off()


#################### CALIBRATE MODES ####################

def calibrate(hw):
    log.info("Starting image capture")
    t = Timer(worker.ImageCapture(hw, range_start=0, range_end=Lights.DMX_MAX_ADDRESS))

    t.start(0)
    t.join()


#################### CAMERA SETTINGS & DOWNLOAD MODES ####################

def download(hw, name, download_all=False, keep=False):
    log.info(f"Downloading sequence '{name}' to {FLAGS.output_path}")
    if download_all:
        # Search for files on camera
        hw.cam.addFiles(hw.cam.listFiles(), FLAGS.sequence_start)
    hw.cam.download(FLAGS.output_path, name, keep=keep)


#################### Light MODES ####################
    
def lights_top(hw):
    lights=[]
    img_latlong = np.zeros((1000,2000,3), dtype='uint8')
    img_uv = np.zeros((1000,1000,3), dtype='uint8')
    cv.circle(img_uv, (500,500), 500, (0, 0, 255), 2)
    for light_entry in hw.config:
        if light_entry['latlong'][0] > 45:
            lights.append(light_entry['id'])
            cv.circle(img_latlong, (int(2000*light_entry['latlong'][1]/360), int(500-500*light_entry['latlong'][0]/90)), 6, (0, 255, 0), 2)
            cv.circle(img_uv, (int(500+500*light_entry['uv'][0]), int(500-500*light_entry['uv'][1])), 6, (0, 255, 0), 2)
        else:
            cv.circle(img_latlong, (int(2000*light_entry['latlong'][1]/360), int(500-500*light_entry['latlong'][0]/90)), 6, (255, 0, 0), 2)
            cv.circle(img_uv, (int(500+500*light_entry['uv'][0]), int(500-500*light_entry['uv'][1])), 6, (255, 0, 0), 2)
    ImgBuffer.SaveEval(img_latlong, "lights_top_latlong")
    ImgBuffer.SaveEval(img_uv, "lights_top_reflection")

def lights_hdri(hw):
    dome = Lightdome(hw.config)
    hdri = ImgBuffer(os.path.join(DATA_BASE_PATH, 'HDRIs', 'blue_photo_studio_1k.exr'), domain=ImgDomain.Lin)
    dome.sampleHdri(hdri)
    img = dome.generateLatLong(hdri)
    ImgBuffer.SaveEval(img.get(), "hdri_latlong")
    img = dome.generateUV()
    ImgBuffer.SaveEval(img.get(), "hdri_uv")
    # TODO: Not implemented
    #rgb = dome.getLights()
    #l = dome.getLightsGray()
    #hw.lights.setDict()

def lights_run(hw):
    log.info("Starting lightrun")
    # Worker class

    log.info(f"Running through {len(hw.config)} lights with IDs {hw.config.getIdBounds()}")
    t = Timer(worker.LightWorker(hw, hw.config))
    t.start(1/15)
    t.join()


#################### EVAL MODES ####################

def eval_cal(path_sequence):
    # Load data
    img_seq = ImgData(path_sequence, video_frames_skip=FLAGS.video_frames_skip)
    img_mask = None
    if os.path.splitext(path_sequence)[1] == '':
        img_mask = ImgData(path_sequence+NAME_MASK_EXT).get(0)
    else:
        img_mask = img_seq.getMaskFrame()
        
    log.info(f"Processing calibration sequencee with {len(img_seq)} frames")

    config=Config()
    eval=Eval()

    # Find center of chrome ball with mask frame
    eval.findCenter(img_mask)
    
    # Loop for all calibration frames
    debug_img = img_mask.asInt().get()
    for id, img in img_seq:
        if not eval.filterBlackframe(img):
            # Process frame
            uv = eval.findReflection(img, id, debug_img)
            if uv is not None:
                config.addLight(id, uv, Eval.SphericalToLatlong(uv))
            img.unload()
        else:
            log.debug(f"Found blackframe '{id}'")
            img.unload()
        
    # Save debug image
    ImgBuffer.SaveEval(debug_img, "reflections")

    # Save config
    log.info(f"Saving config to '{FLAGS.config_path}' with lights from ID {config.getIdBounds()}")
    config.save(FLAGS.config_path, FLAGS.config_name)


#################### DEBUG MODES ####################

def debug(hw):
    # Debug code for testing image & video capture, downloading and changing settings of camera
    pass

if __name__ == '__main__':
    app.run(main)
