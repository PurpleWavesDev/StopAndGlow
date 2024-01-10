# Imports
import sys
import os
import io
import time
from collections import namedtuple
from importlib import reload
from typing import Any

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
import src.worker as worker
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
flags.DEFINE_enum('mode', 'capture_lights', ['capture_lights', 'capture_hdri', 'calibrate', 'download', 'eval_cal', 'lights_animate', 'lights_hdri', 'lights_run', 'debug'], 'What the script should do.')
flags.DEFINE_enum('capture_mode', 'quick', ['jpg', 'raw', 'quick'], 'Capture modes: Image (jpg or raw) or video/quick.')
flags.DEFINE_enum('loglevel', 'INFO', ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], 'Level of logging.')
# Configuration
flags.DEFINE_string('config_path', '../HdM_BA/data/config', 'Where the configurations should be stored.')
flags.DEFINE_string('config_name', 'lightdome.json', 'Name of config file.')
flags.DEFINE_string('config_ids_name', 'available_lights.json', 'Name of config to read available light IDs from. Only used for calibration.') # 
# Sequence 
flags.DEFINE_string('output_path', '../HdM_BA/data', 'Where the image data should be written to.')
flags.DEFINE_string('sequence_name', '', 'Sequence name to download and/or evaluate.')
flags.DEFINE_integer('sequence_start', 0, 'Frame count starting from this number for downloads', lower_bound=0)
flags.DEFINE_boolean('keep_sequence', False, 'Keep images on camera after downloading.')
# Additional resources
flags.DEFINE_string('input_hdri', 'HDRIs/pretville_cinema_1k.exr', 'Name/Path of HDRI that is used for sky dome sampling.')
# Capture settings
flags.DEFINE_integer('video_frames_skip', 1, 'Frames to skip between valid frames in video sequence', lower_bound=0) # TODO: Could be hard-coded
flags.DEFINE_float('video_fps', 29.97, 'Frame rate for the video capture')


def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')

    ### Eval Modes without hardware requirements ###
    if FLAGS.mode == 'eval_cal':
        name = "calibration" if FLAGS.sequence_name == "" else FLAGS.sequence_name
        eval_cal(os.path.join(FLAGS.output_path, name))

    else:
        # Prepare hardware for tasks
        hw = HW(Cam(), Lights(), Config(os.path.join(FLAGS.config_path, FLAGS.config_name)))

        # Execute task for requested mode
        ### Capture Modes ###
        if FLAGS.mode == 'capture_lights':
            capture(hw) # TODO: capture method
            name = "capture" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            download(hw, name, keep=FLAGS.keep_sequence)
        elif FLAGS.mode == 'capture_hdri':
            # Capture sequence of color channels from HDRI
            hdri = ImgBuffer(os.path.join(DATA_BASE_PATH, FLAGS.input_hdri), domain=ImgDomain.Lin)
            captureHdri(hw, hdri)
        elif FLAGS.mode == 'calibrate':
            name = "calibration" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            # Capture with all lights on for masking frame
            captureSilhouette(hw)
            download(hw, name+NAME_MASK_EXT, keep=False)
            capture(hw)
            download(hw, name, keep=FLAGS.keep_sequence)
            
        ### Download only ###
        elif FLAGS.mode == 'download':
            name = "download" if FLAGS.sequence_name == "" else FLAGS.sequence_name
            download(hw, name, download_all=True, keep=FLAGS.keep_sequence)
            
        ### Light Modes ###
        elif FLAGS.mode == 'lights_animate':
            lightsAnimate(hw)
        elif FLAGS.mode == 'lights_hdri':
            lightsHdriRotate(hw)
        elif FLAGS.mode == 'lights_run':
            lightsConfigRun(hw)
            
        ### Debug Mode ###
        elif FLAGS.mode == 'debug':
            debug(hw)
        
        # Light default state
        lightsTop(hw, brightness=80)
        #hw.lights.off()


#################### CAPTURE MODES ####################

def capture(hw):
    log.info("Starting image capture")
    t = Timer(worker.LightListWorker(hw, hw.config.getIds(), trigger_capture=True))
    t.start(0)
    t.join()

def captureQuick(hw):
    log.info("Starting quick capture (video)")
    # Worker & Timer
    # TODO: Silhouette
    t = Timer(worker.VideoListWorker(hw, hw.config.getIds()))
    t.start(2/FLAGS.video_fps)
    t.join()

def captureSilhouette(hw):
    # TODO: Silhouette is all lights rn
    frame = [127] * Lights.DMX_MAX_ADDRESS
    hw.lights.setFrame(frame)
    hw.lights.write()

    # Trigger camera
    hw.cam.capturePhoto(0)
    hw.lights.off()
    
def captureHdri(hw, hdri):
    dome = Lightdome(hw.config)
    dome.sampleHdri(hdri)

    # Send samples to dome & take pictures
    rgb = dome.getLights()
    # R
    hw.lights.setLights(rgb, 0)
    hw.lights.write()
    hw.cam.capturePhoto(0)
    # G
    hw.lights.setLights(rgb, 1)
    hw.lights.write()
    hw.cam.capturePhoto(1)
    # B
    hw.lights.setLights(rgb, 2)
    hw.lights.write()
    hw.cam.capturePhoto(2)
    # Get channels and stack them
    r = hw.cam.getImage(0, DATA_BASE_PATH, 'HDRI_RGB').r()
    g = hw.cam.getImage(1, DATA_BASE_PATH, 'HDRI_RGB').g()
    b = hw.cam.getImage(2, DATA_BASE_PATH, 'HDRI_RGB').b()
    # TODO: Stacking


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
    
def lightsTop(hw, latitude=60, brightness: int = 255):
    dome = Lightdome(hw.config)
    # Sample top lights
    dome.sampleLatLong(lambda latlong: ImgBuffer.FromPix(brightness) if latlong[0] > latitude else ImgBuffer.FromPix(0))
    # Save images
    img = dome.generateLatLong()
    ImgBuffer.SaveEval(img.get(), "top_latlong")
    img = dome.generateUV()
    ImgBuffer.SaveEval(img.get(), "top_uv")
    # Show on dome
    hw.lights.setLights(dome.getLights(), 0)
    hw.lights.write()


def lightsAnimate(hw):
    # Function for
    dome = Lightdome(hw.config)
    def fn_lat(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleLatLong(lambda latlong: ImgBuffer.FromPix(50) if latlong[0] > 90-(i*2) else ImgBuffer.FromPix(0))
        lights.setLights(dome.getLights())
        return i<45
    def fn_long(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleLatLong(lambda latlong: ImgBuffer.FromPix(50) if latlong[1] < i*8 and latlong[1] > i*4-15 else ImgBuffer.FromPix(0))
        lights.setLights(dome.getLights())
        return i<45

    for _ in range(3):
        t = Timer(worker.LightFnWorker(hw, fn_lat, parameter=dome))
        t.start(1/10)
        t.join()

        t = Timer(worker.LightFnWorker(hw, fn_long, parameter=dome))
        t.start(1/10)
        t.join()

def lightsHdriRotate(hw):
    dome = Lightdome(hw.config)
    hdri = ImgBuffer(os.path.join(DATA_BASE_PATH, FLAGS.input_hdri), domain=ImgDomain.Lin)
    dome.sampleHdri(hdri)
    img = dome.generateLatLong(hdri)
    ImgBuffer.SaveEval(img.get(), "hdri_latlong")
    img = dome.generateUV()
    ImgBuffer.SaveEval(img.get(), "hdri_uv")
    
    # Function for
    def fn(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleProcessedHdri(i*3) # 10 degree / second
        lights.setLights(dome.getLights())
        return i<360
    
    t = Timer(worker.LightFnWorker(hw, fn, parameter=dome))
    t.start(1/10)
    t.join()


def lightsConfigRun(hw):
    log.info(f"Running through {len(hw.config)} lights with IDs {hw.config.getIdBounds()}")
    t = Timer(worker.LightListWorker(hw, hw.config.getIds()))
    t.start(1/15)
    t.join()


#################### EVAL MODES ####################

def eval_cal(path_sequence):
    # Load data
    img_seq = ImgData()
    img_mask = None
    if os.path.splitext(path_sequence)[1] == '':
        # Folder
        img_seq.loadFolder(path_sequence)
        img_mask = ImgData(path_sequence+NAME_MASK_EXT).get(0)
    else:
        # TODO: video_frames_skip=FLAGS.video_frames_skip
        frame_list = Config(os.path.join(FLAGS.config_path, FLAGS.config_ids_name)).getIds()
        img_seq.loadVideo(path_sequence, frame_list)
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
