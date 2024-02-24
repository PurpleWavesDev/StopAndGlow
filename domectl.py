# Enable OpenCV EXR support
import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

# Imports
import sys
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
from src.sequence import Sequence
from src.lightdome import Lightdome
from src.eval import Eval
from src.rti import RtiRenderer
from src.img_op import *
from src.cam_op import *
from src.viewer import *
import src.ti_base as tib

# Types
HW = namedtuple("HW", ["cam", "lights", "config"])

# Globals
FLAGS = flags.FLAGS

# Global flag defines
# Mode and logging
flags.DEFINE_enum('mode', 'capture_lights', ['capture_lights', 'capture_rti', 'capture_hdri', 'capture_cal', 'eval_rti', 'eval_hdri', 'eval_stack', 'eval_linearize', 'eval_cal','relight_simple', 'relight_rti', 'relight_ml', 'viewer_rti', 'lights_hdri', 'lights_animate', 'lights_run', 'lights_ambient', 'lights_off', 'cam_deleteall', 'cam_stopvideo'], 'What the script should do.')
flags.DEFINE_enum('capture_mode', 'jpg', ['jpg', 'raw', 'quick'], 'Capture modes: Image (jpg or raw) or video/quick.')
flags.DEFINE_enum('loglevel', 'INFO', ['CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], 'Level of logging.')
# Configuration
flags.DEFINE_string('config_path', '../HdM_BA/data/config', 'Where the configurations should be stored.')
flags.DEFINE_string('config_name', 'lightdome.json', 'Name of input config file.')
flags.DEFINE_string('config_output_name', '', "Name of config to write calibration data to. Default is 'lightdome' and current date & time.")
# Sequence 
flags.DEFINE_string('sequence_path', '../HdM_BA/data', 'Where the image data should be written to.')
flags.DEFINE_string('sequence_name', '', 'Sequence name to download and/or evaluate. Default is type of capture current date & time.')
flags.DEFINE_string('sequence_output_name', '', 'Sequence name for processed sequences e.g. stacking.')
flags.DEFINE_enum  ('sequence_domain', 'guess', ['guess', 'lin', 'sRGB'], 'Domain of sequence. Default for EXR is linear, sRGB for PNGs and JPGs.')
flags.DEFINE_boolean('sequence_keep', False, 'Keep images on camera after downloading.')
flags.DEFINE_boolean('sequence_save', True, 'If captured sequences should be saved or discarded after evaluation.')
# Capture settings
# TODO: Should be hard-coded
flags.DEFINE_integer('video_frames_skip', 2, 'Frames to skip between valid frames in video sequence', lower_bound=0)
flags.DEFINE_float('video_fps', 25, 'Frame rate for the video capture.')
# Additional resources
flags.DEFINE_string('input_hdri', 'HDRIs/pretville_cinema_1k.exr', 'Name/Path of HDRI that is used for sky dome sampling.')
flags.DEFINE_float('hdri_rotation', 0, 'Rotation of HDRI in degrees.', lower_bound=0, upper_bound=360)


def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')

    # Prepare hardware for tasks
    hw = HW(Cam(), Lights(), Config(os.path.join(FLAGS.config_path, FLAGS.config_name)))
    tib.init(on_cuda=True, debug=True)
    mode, mode_type = FLAGS.mode.split("_", 1)
    sequence = None

    ### Camera quick controlls ###
    if 'cam' in mode:
        if 'stopvideo' in mode_type:
            triggerVideoEnd()
        elif 'deleteall' in mode_type:
            # Delete all files on camera
            hw.cam.deleteAll()

        #CamOp.FindMaxExposure(hw.cam)
        #hw.cam.setIso('100')
        #hw.cam.setAperture('8')
        # All done, return
        return
    
    ### Load image sequence, either bei capturing or loading sequence from disk ###
    if mode == "capture":
        # Init lights
        hw.lights.getInterface()
        name = FLAGS.sequence_name if FLAGS.sequence_name != '' else datetime.datetime.now().strftime("%Y%m%d_%H%M") + '_' + mode_type # 240116_2333_cal
        
        # Set configuration for camera
        # TODO! Organize better
        if not hw.cam.isVideoMode():
            if FLAGS.capture_mode == 'raw':
                hw.cam.setImgFormat(CamImgFormat.Raw)
            else:
                hw.cam.setImgFormat(CamImgFormat.JpgMedium)
            #hw.cam.setExposure('1/100')
            
        # Capturing for all modes
        if 'hdri' in mode_type:
            captureHdri(hw)
        else:
            capture(hw)            
        
        # Default light
        lightsTop(hw, brightness=80)
        
        # Sequence download, evaluation of video not necessary for capture only
        sequence = download(hw, name, keep=FLAGS.sequence_keep, save=FLAGS.sequence_save)
    
    
    ### Separate lights only modes from evaluation ###
    if mode == 'lights':
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
        # Split sequence
        names = FLAGS.sequence_name.split(',')
        # Load data
        if len(names) == 1:
            sequence = load(FLAGS.sequence_name, hw.config)
            if len(sequence) == 0:
                log.error("Empty sequence, aborting")
                return
        else:
            sequence = []
            # Load sequence for every comma separated name
            for seq in names:
                sequence.append(load(seq, hw.config))
    
        if mode == 'eval':
            match mode_type:
                case 'rti':
                    evalRti(sequence, hw.config)
                case 'hdri':
                    evalHdri(sequence)
                case 'stack':
                    output_name = FLAGS.sequence_output_name if FLAGS.sequence_output_name != '' else datetime.datetime.now().strftime("%Y%m%d_%H%M") + '_' + mode_type
                    evalStack(sequence, output_name)
                case 'linearize':
                    output_name = FLAGS.sequence_output_name if FLAGS.sequence_output_name != '' else f"{os.path.splitext(FLAGS.sequence_name)[0]}_linear"
                    evalLinearize(sequence, output_name)
                case 'cal':
                    evalCal(sequence)
        elif mode == 'relight':
            name = FLAGS.sequence_output_name if FLAGS.sequence_output_name != '' else os.path.splitext(FLAGS.sequence_name)[0]
            match mode_type:
                case 'simple':
                    relightSimple(sequence, hw.config, name+'_lit_simp')
                case 'rti':
                    relightRti(sequence, name+'_lit_rti')
                case 'ml':
                    relightMl(sequence, hw.config, name+'_lit_ml')
        elif mode == 'viewer':
            match mode_type:
                case 'rti':
                    viewerRti(sequence)


                    

#################### CAPTURE MODES ####################

def capture(hw):
    if FLAGS.capture_mode == 'quick':
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
    t = Timer(worker.VideoListWorker(hw, hw.config.getIds(), subframe_count=1)) # TODO: Subframe count right? Should be FLAGS.video_frames_skip probably?

    # Capture
    hw.cam.triggerVideoStart()
    time.sleep(1)
    t.start((1+FLAGS.video_frames_skip) / FLAGS.video_fps)
    t.join()
    time.sleep(1)
    hw.cam.triggerVideoEnd()

    
def captureHdri(hw):
    # Load HDRI
    hdri = ImgBuffer(os.path.join(FLAGS.sequence_path, FLAGS.input_hdri), domain=ImgDomain.Lin)
    
    # Sample domelights
    dome = Lightdome(hw.config)
    dome.processHdri(hdri)
    dome.sampleLightsForHdri(longitude_offset=FLAGS.hdri_rotation)
    rgb = dome.getLights()

    if 'quick' in FLAGS.capture_mode:
        captureHdriVideo(hw, rgb)
    else:
        captureHdriImg(hw, rgb)


def captureHdriVideo(hw, rgb):
    log.info("Starting quick HDRI capture (video)")
    # Worker & Timer
    t = Timer(worker.VideoSampleWorker(hw, rgb))

    # Capture
    hw.cam.triggerVideoStart()
    time.sleep(1)
    t.start((1+FLAGS.video_frames_skip) / FLAGS.video_fps)
    t.join()
    time.sleep(0.5)
    hw.cam.triggerVideoEnd()


def captureHdriImg(hw, rgb):
    log.info("Starting HDRI capture")
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



#################### Light MODES ####################
    
def lightsTop(hw, latitude=60, brightness: int = 255):
    dome = Lightdome(hw.config)
    # Sample top lights
    dome.sampleLatLong(lambda latlong: ImgBuffer.FromPix(brightness) if latlong[0] > latitude else ImgBuffer.FromPix(0))
    # Save images
    img = dome.generateLatLong()
    ImgOp.SaveEval(img.get(), "top_latlong")
    img = dome.generateUV()
    ImgOp.SaveEval(img.get(), "top_uv")
    # Show on dome
    hw.lights.setLights(dome.getLights(), 0)
    hw.lights.write()


def lightsAnimate(hw):
    # Function for
    dome = Lightdome(hw.config)
    def fn_lat(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleLatLong(lambda latlong: ImgBuffer.FromPix(50) if latlong[0] > 90-(i*2) else ImgBuffer.FromPix(0))
        lights.setLights(dome.getLights())
        return i<60 # i<45
    def fn_long(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleLatLong(lambda latlong: ImgBuffer.FromPix(80 * max(0, 1 - (i*8-latlong[1])/90)) if latlong[1] < i*8 else ImgBuffer.FromPix(0))
        lights.setLights(dome.getLights())
        return i<60 # i<45

    for _ in range(3):
        t = Timer(worker.LightFnWorker(hw, fn_lat, parameter=dome))
        t.start(1/10)
        t.join()

        t = Timer(worker.LightFnWorker(hw, fn_long, parameter=dome))
        t.start(1/10)
        t.join()

def lightsHdriRotate(hw):
    dome = Lightdome(hw.config)
    hdri = ImgBuffer(os.path.join(FLAGS.sequence_path, FLAGS.input_hdri), domain=ImgDomain.Lin)
    dome.processHdri(hdri)
    dome.sampleLightsForHdri(0)
    img = dome.generateLatLong(hdri)
    ImgOp.SaveEval(img.get(), "hdri_latlong")
    img = dome.generateUV()
    ImgOp.SaveEval(img.get(), "hdri_uv")
    
    # Function for
    def fn(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleLightsForHdri(i*3) # 10 degree / second
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

def evalRti(img_seq, config):
    log.info(f"Generate RTI Data from image sequence")
    
    # Scale down
    #for id, img in img_seq:
    #    img = img.scale(0.5, False)
    #    img_seq[id] = img
    
    # Calculate RTI
    rti = RtiRenderer()
    rti.process(img_seq, config, {'order': 2})
    
    # Save RTI sequence
    rti_seq = rti.get()
    name = FLAGS.sequence_output_name if FLAGS.sequence_output_name != "" else FLAGS.sequence_name + "_rti"
    rti_seq.saveSequence(name, FLAGS.sequence_path, ImgFormat.EXR)


def evalHdri(img_seq):
    log.info(f"Processing HDRI RGB sequence")

    # Get channels and stack them
    r = img_seq[0].r()
    g = img_seq[1].g()
    b = img_seq[2].b()
    
    # Stacking
    path = os.path.join(os.path.split(img_seq[0].getPath())[0], 'HDRI_stacked')
    rgb = ImgOp.StackChannels([r, g, b], path)
    rgb.setFormat(ImgFormat.JPG)
    rgb.save()

def evalStack(sequences, output_name, cam_response=None):
    stacked_seq = Sequence()
    sequence_count = len(sequences)
            
    if False: #cam_response is None:
        # List of current frames
        frames = [seq.getMaskFrame() for seq in sequences]
        cam_response = ImgOp.CameraResponse(frames) # TODO Stuck
        for i in range(len(frames)):
            frames[i].setPath(os.path.join(FLAGS.sequence_path, output_name, f"mask_{i:03d}"))
            frames[i].save(ImgFormat.JPG)
    
    # Iterate over frames
    for i in range(len(sequences[0])):
        # List of current frames
        frames = [seq.get(i) for seq in sequences]
        id = sequences[0].getKeys()[i]
                
        if cam_response is None:
            cam_response = ImgOp.CameraResponse(frames) # TODO Stuck
            for i in range(len(frames)):
                frames[i].setPath(os.path.join(FLAGS.sequence_path, output_name, f"first_{i:03d}"))
                frames[i].save(ImgFormat.JPG)
        
        path = os.path.join(FLAGS.sequence_path, output_name, f"{output_name}_{id:03d}")
        stacked_seq.append(ImgOp.ExposureStacking(frames, cam_response, path=path), id)
        
        # Save & unload frame
        stacked_seq[id].unload(save=True)
    
    # Return sequence with stacked images       
    return stacked_seq

def evalLinearize(img_seq, output_name):
    for i in range(len(img_seq)):
        img = img_seq.get(i).asDomain(ImgDomain.Lin, as_float=True)
        id = img_seq.getKeys()[i]
        img.setPath(os.path.join(FLAGS.sequence_path, output_name, f"{output_name}_{id:03d}"))
        img.setFormat(ImgFormat.EXR)
        #img = img.scale(0.5) # TODO
        img.unload(save=True)

def evalCal(img_seq):
    log.info(f"Processing calibration sequencee with {len(img_seq)} frames")

    new_config=Config()
    eval=Eval()
    img_mask = img_seq.getMaskFrame()

    # Find center of chrome ball with mask frame
    eval.findCenter(img_mask)
    
    # Loop through all calibration frames
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
    ImgOp.SaveEval(debug_img, "reflections")

    # Save config
    name = FLAGS.config_output_name if FLAGS.config_output_name != '' else datetime.datetime.now().strftime("%Y%m%d_%H%M") + '_calibration.json' # 240116_2333_calibration.json
    log.info(f"Saving config as '{name}' with {len(new_config)} lights from ID {new_config.getIdBounds()}")
    new_config.save(FLAGS.config_path, name)



#################### RELIGHT MODES ####################

def relightSimple(img_seq, config, output_name):
    # Deine Funktion, Iris :)
    log.info(f"Generate HDRI Lighting from Sequence")

    dome = Lightdome(config)
    hdri = ImgBuffer(os.path.join(FLAGS.sequence_path, FLAGS.input_hdri), domain=ImgDomain.Lin)
    dome.processHdri(hdri)

    # Sequence generator
    for i in range(72):
        lighting = dome.generateLightingFromSequence(img_seq, longitude_offset=i*5)
        lighting.setPath(os.path.join(FLAGS.sequence_path, output_name, f"{output_name}_{i:03d}"))
        lighting.set(lighting.get()*40)
        lighting = lighting.asDomain(ImgDomain.sRGB)
        lighting.setFormat(ImgFormat.JPG)
        lighting.save()
        
    return
    # Generate scene with HDRI lighting 
    lighting = dome.generateLightingFromSequence(img_seq, longitude_offset=FLAGS.hdri_rotation)

    lighting.setPath(os.path.join(FLAGS.sequence_path, output_name, output_name))
    lighting.setFormat(ImgFormat.EXR)
    lighting.save()


def relightRti(img_seq, output_name):
    log.info(f"Generate HDRI Lighting from RTI data")
    
    rti = Rti(img_seq.get(0).resolution())
    rti.load(img_seq)
    
    # Sequence generator
    for i in range(36):
        lighting = rti.sampleLight((45, i*10))
        lighting.setPath(os.path.join(FLAGS.sequence_path, output_name, f"{output_name}_{i:03d}"))
        lighting.set(lighting.get()*20)
        lighting = lighting.asDomain(ImgDomain.sRGB)
        lighting.setFormat(ImgFormat.JPG)
        lighting.save()
    return    
    
    ImgOp.SaveEval(rti.sampleLight((45,0)).get(), "RTI1", ImgFormat.EXR)
    ImgOp.SaveEval(rti.sampleLight((45,180)).get(), "RTI2", ImgFormat.EXR)
    ImgOp.SaveEval(rti.sampleLight((45,360)).get(), "RTI3", ImgFormat.EXR)
    ImgOp.SaveEval(rti.sampleLight((0, 0)).get(), "RTI4", ImgFormat.EXR)
    ImgOp.SaveEval(rti.sampleLight((90, 0)).get(), "RTI5", ImgFormat.EXR)
    
    
    hdri = ImgBuffer(os.path.join(FLAGS.sequence_path, FLAGS.input_hdri), domain=ImgDomain.Lin)
    
    # Generate scene with HDRI lighting
    lighting = rti.sampleHdri(hdri)
    
    lighting.setPath(os.path.join(FLAGS.sequence_path, output_name, output_name))
    lighting.setFormat(ImgFormat.EXR)
    lighting.save()
    
    
def relightMl(img_seq, config, output_name):
    pass


#################### VIEWER MODES ####################

def viewerRti(img_seq):
    log.info(f"Lauching viewer")
    
    # HDRI
    hdri = ImgBuffer(os.path.join(FLAGS.sequence_path, FLAGS.input_hdri), domain=ImgDomain.Lin)
    res_y, res_x = hdri.get().shape[:2]
    blur_size = int(15*res_y/100)
    blur_size += 1-blur_size%2 # Make it odd
    hdri.set(cv.GaussianBlur(hdri.get(), (blur_size, blur_size), -1))
    
    viewer = Viewer()
    viewer.setSequences(rti_factors=img_seq)
    viewer.setHdris([hdri])
    viewer.launch()
    


#################### CAMERA SETTINGS & DOWNLOAD HELPERS ####################

def download(hw, name, keep=False, save=False):
    """Download from camera"""
    log.debug(f"Downloading sequence '{name}' to {FLAGS.sequence_path}")
    sequence = Sequence()
    if 'quick' in FLAGS.capture_mode:
        sequence = hw.cam.getVideoSequence(FLAGS.sequence_path, name, hw.config.getIds(), keep=keep)
    else:
        sequence = hw.cam.getSequence(FLAGS.sequence_path, name, keep=keep)
        if save:
            for _, img in sequence:
                img.save(format = ImgFormat.EXR if FLAGS.capture_mode == 'raw' else ImgFormat.JPG)
    return sequence
    
def load(name, config):
    """Load from disk"""
    sequence = Sequence()
    
    path = os.path.join(FLAGS.sequence_path, name)
    if os.path.splitext(name)[1] == '':
        # Load folder
        domain = ImgDomain.Lin
        match FLAGS.sequence_domain:
            case 'guess':
                domain = ImgDomain.Keep
            case 'sRGB':
                domain = ImgDomain.sRGB
        sequence.loadFolder(path, domain)
    else:
        # Load video
        sequence.loadVideo(path, config.getIds(), video_frames_skip=FLAGS.video_frames_skip)
    
    return sequence


#################### MODES END ####################

if __name__ == '__main__':
    app.run(main)
