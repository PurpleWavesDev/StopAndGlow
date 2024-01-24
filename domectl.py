# Imports
import sys
import os
import io
import time
import datetime
from collections import namedtuple
from importlib import reload
from typing import Any

# Flags and logging
from absl import app
from absl import flags
import logging as log

# DMX, Config and Camera interfaces
from src.camera import *
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
flags.DEFINE_enum('mode', 'capture_lights', ['capture_lights', 'capture_rti', 'capture_hdri', 'capture_cal', 'eval_rti', 'eval_hdri', 'eval_cal', 'lights_hdri', 'lights_animate', 'lights_run', 'lights_ambient', 'lights_off'], 'What the script should do.')
flags.DEFINE_enum('capture_mode', 'jpg', ['jpg', 'raw', 'quick'], 'Capture modes: Image (jpg or raw) or video/quick.')
flags.DEFINE_enum('loglevel', 'INFO', ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], 'Level of logging.')
# Configuration
flags.DEFINE_string('config_path', '../HdM_BA/data/config', 'Where the configurations should be stored.')
flags.DEFINE_string('config_name', 'lightdome.json', 'Name of input config file.')
flags.DEFINE_string('config_output_name', '', "Name of config to write calibration data to. Default is 'lightdome' and current date & time.")
# Sequence 
flags.DEFINE_string('sequence_path', '../HdM_BA/data', 'Where the image data should be written to.')
flags.DEFINE_string('sequence_name', '', 'Sequence name to download and/or evaluate. Default is type of capture current date & time.')
flags.DEFINE_boolean('sequence_keep', False, 'Keep images on camera after downloading.')
# Capture settings
# TODO: Should be hard-coded
flags.DEFINE_integer('video_frames_skip', 2, 'Frames to skip between valid frames in video sequence', lower_bound=0)
flags.DEFINE_float('video_fps', 25, 'Frame rate for the video capture')
# Additional resources
flags.DEFINE_string('input_hdri', 'HDRIs/pretville_cinema_1k.exr', 'Name/Path of HDRI that is used for sky dome sampling.')


def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')

    # Prepare hardware for tasks
    hw = HW(Cam(), Lights(), Config(os.path.join(FLAGS.config_path, FLAGS.config_name)))
    mode, mode_type = FLAGS.mode.split("_", 1)
    sequence = None
    sequence2 = None

    # Delete all files on camera
    #hw.cam.deleteAll()
    # TODO: Test code for image capture settings
    #hw.cam.setIso('100')
    #hw.cam.setAperture('8')
    #if not hw.cam.isVideoMode():
    #    hw.cam.setImgFormat(CamImgFormat.JpgSmall)
    #    hw.cam.setExposure('1/100')
    
    ### Load image sequence, either bei capturing or loading sequence from disk ###
    if "capture" in mode:
        # Init lights
        hw.lights.getInterface()
        name = FLAGS.sequence_name if FLAGS.sequence_name != '' else datetime.datetime.now().strftime("%Y%m%d_%H%M") + '_' + mode_type # 240116_2333_cal
        
        # Capturing for all modes
        if 'hdri' in mode_type:
            captureHdri(hw)
        else:
            capture(hw)            
        
        # Default light
        lightsTop(hw, brightness=80)
        
        # Sequence download
        sequence = download(hw, name, keep=FLAGS.sequence_keep, save=True)
    

    elif not 'lights' in mode:
        # Load data
        sequence = load(FLAGS.sequence_name, hw.config)
    
    ### Separate lights only modes from evaluation ###
    if 'lights' in mode:
        # Lights only modes

        # Init lights
        hw.lights.getInterface()

        match mode_type:
            case 'hdri':
                lightsHdriRotate(hw)
            case 'animate':
                lightsAnimate(hw)
            case 'run':
                lightsConfigRun(hw)
            case 'off':
                hw.lights.off()
            case 'ambient':
                # Ambient light will be turned on anyway, just pass
                pass

        # Default light
        if not 'off' in mode_type:
            lightsTop(hw, brightness=80)
    
    else:
        match mode_type:
            case 'rti':
                evalRti(sequence)
            case 'hdri':
                evalHdri(sequence)
            case 'cal':
                evalCal(sequence)


                    

#################### CAPTURE MODES ####################

def capture(hw):
    if 'quick' in FLAGS.capture_mode:
        captureVideo(hw)
    else:
        captureImg(hw)
    
def captureImg(hw):
    log.info("Starting image capture")
    t = Timer(worker.LightListWorker(hw, hw.config.getIds(), trigger_capture=True))
    t.start(0)
    t.join()

def captureVideo(hw):
    # TODO: Silhouette

    log.info("Starting quick capture (video)")
    # Worker & Timer
    t = Timer(worker.VideoListWorker(hw, hw.config.getIds(), subframe_count=1))

    # Capture
    hw.cam.triggerVideoStart()
    time.sleep(1)
    t.start((1+FLAGS.video_frames_skip) / FLAGS.video_fps)
    t.join()
    time.sleep(1)
    hw.cam.triggerVideoEnd()

    
def captureHdri(hw):
    # Load HDRI
    hdri = ImgBuffer(os.path.join(DATA_BASE_PATH, FLAGS.input_hdri), domain=ImgDomain.Lin)
    
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


    hw.cam.capturePhoto(99)



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

def evalRti(img_seq):
    pass

def evalHdri(img_seq):
    log.info(f"Processing HDRI image sequence")

    # Get channels and stack them
    r = img_seq[0].r()
    g = img_seq[1].g()
    b = img_seq[2].b()
    
    # TODO: Stacking

def evalCal(img_seq):
    log.info(f"Processing calibration sequencee with {len(img_seq)} frames")

    new_config=Config()
    eval=Eval()
    img_mask = img_seq.getMaskFrame()

    # Find center of chrome ball with mask frame
    eval.findCenter(img_mask)
    
    # Loop for all calibration frames
    debug_img = img_mask.asInt().get()
    for id, img in img_seq:
        if not eval.filterBlackframe(img):
            # Process frame
            uv = eval.findReflection(img, id, debug_img)
            if uv is not None:
                new_config.addLight(id, uv, Eval.SphericalToLatlong(uv))
            img.unload()
        else:
            log.debug(f"Found blackframe '{id}'")
            img.unload()
        
    # Save debug image
    ImgBuffer.SaveEval(debug_img, "reflections")

    # Save config
    name = FLAGS.config_output_name if FLAGS.config_output_name != '' else datetime.datetime.now().strftime("%Y%m%d_%H%M") + '_calibration.json' # 240116_2333_calibration.json
    log.info(f"Saving config as '{name}' with {len(new_config)} lights from ID {new_config.getIdBounds()}")
    new_config.save(FLAGS.config_path, name)



#################### CAMERA SETTINGS & DOWNLOAD HELPERS ####################

def download(hw, name, keep=False, save=False):
    """Download from camera"""
    log.debug(f"Downloading sequence '{name}' to {FLAGS.sequence_path}")
    sequence = ImgData()
    if 'quick' in FLAGS.capture_mode:
        sequence = hw.cam.getVideoSequence(FLAGS.sequence_path, name, hw.config.getIds(), keep=keep)
    else:
        sequence = hw.cam.getSequence(FLAGS.sequence_path, name, keep=keep)
        if save:
            for img in sequence:
                img.save(format=ImgFormat.PNG)
    return sequence
    
def load(name, config):
    """Load from disk"""
    sequence = ImgData()
    
    path = os.path.join(FLAGS.sequence_path, name)
    if os.path.splitext(name)[1] == '':
        # Load folder
        sequence.loadFolder(path)
    else:
        # Load video
        sequence.loadVideo(path, config.getIds(), video_frames_skip=FLAGS.video_frames_skip)
    
    return sequence


#################### MODES END ####################

if __name__ == '__main__':
    app.run(main)
