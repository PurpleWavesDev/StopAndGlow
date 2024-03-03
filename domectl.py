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
from src.calibrate import Calibrate
from src.img_op import *
from src.cam_op import *
from src.viewer import *
import src.ti_base as tib
# Renderer
from src.renderer.renderer import Renderer
from src.renderer.rti import RtiRenderer
from src.renderer.rgbstack import RgbStacker
from src.renderer.lightstack import LightStacker

# Types
HW = namedtuple("HW", ["cam", "lights", "config"])

# Globals
FLAGS = flags.FLAGS
DEBUG = hasattr(sys, 'gettrace') and sys.gettrace() is not None

### Example of usage for domectl
# domectl --capture --hdr --seq-type=lights|hdri|fullrun --seq-name="" --seq-domain=keep|linear|srgb --seq-save --seq-convert
# domectl --process --eval-type=cal|hdri|lightstack|rti|expostack|convert --eval-folder="" --eval-name=""
# domectl --viewer --headless --record --record-folder="" --record-name="" --hdri-folder="" --hdri-name=""
# domectl --camctl=none|stop|erase
# domectl --lightctl=none|on|off|run|anim-latlong|hdri --brightness=0-255 --limiter=0-255

### Global flag defines ###
# General
flags.DEFINE_enum('loglevel', 'INFO', ['ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE'], 'Level of logging.')
# Capture
flags.DEFINE_bool('capture', False, "Set this flag to capture footage instead of loading it from disk.")
flags.DEFINE_bool('hdr', False, "If set, capture will be either raw images or multiple videos for exposure stacking, depending on the camera mode.")
flags.DEFINE_integer('vid_frames_skip', 2, 'Frames to skip between valid frames in video sequence', lower_bound=0)
flags.DEFINE_float('vid_fps', 25, 'Frame rate for the video capture.')
flags.DEFINE_boolean('vid_safe', True, "Captures two pictures for the same frame and discharges the first one.")
# Sequence settings
flags.DEFINE_enum('seq_type', 'lights', ["lights", "hdri", "fullrun"], "Sequence consists of images from all lights of the current config, three images for RGB channel stacking or a full run for all light IDs without config.")
flags.DEFINE_enum('seq_domain', 'keep', ['keep', 'lin', 'srgb'], 'Domain of sequence, default for EXR is linear, sRGB for PNGs and JPGs.')
flags.DEFINE_string('seq_folder', '../HdM_BA/data/capture', 'Where the image data should be written to.')
flags.DEFINE_string('seq_name', '', 'Name of captured sequence or folder/file to load, default is current date & time + type of capture.')
flags.DEFINE_bool('seq_save', True, "Save downloaded images to disk.")
flags.DEFINE_bool('seq_convert', False, "Convert to image files if a video was captured.")
# Calibration
flags.DEFINE_string('cal_folder', '../HdM_BA/data/config', 'Folder for light calibration.')
flags.DEFINE_string('cal_name', 'lightdome.json', 'Name of calibration file to be loaded or generated.')
flags.DEFINE_string('new_cal_name', 'lightdome.json', 'Name of calibration file to be loaded or generated.')
# HDRI
flags.DEFINE_string('hdri_folder', '../HdM_BA/data/hdri', 'Folder for HDRI environment maps.')
flags.DEFINE_string('hdri_name', '', 'Name of HDRI image to be used for processing.')
flags.DEFINE_float('hdri_rotation', 0.0, 'Rotation of HDRI in degrees.', lower_bound=0, upper_bound=360)
# Processing
flags.DEFINE_bool('process', False, "Set this flag to enable processing of recorded footage.")
flags.DEFINE_enum('eval_type', 'pass', ["cal", "rgbstack", "lightstack", "rti", "expostack", "convert", 'pass'], "How the sequence should be processed or interpreted by the viewer.")
flags.DEFINE_bool('eval_dontsave', False, "Set this flag to discard evaluation data after processing.")
flags.DEFINE_string('eval_folder', '../HdM_BA/data/processed', 'Folder for HDRI environment maps.')
flags.DEFINE_string('eval_name', '', 'Name of HDRI image to be used for processing.')
# Viewer
flags.DEFINE_bool('viewer', False, "Set this flag to launch the viewer with the loaded or processed data.")
flags.DEFINE_bool('record', False, "Set this flag to record a 360° environment turn in headless mode.")
flags.DEFINE_string('rec_folder', '../HdM_BA/data/rec', 'Folder for recorded renderings.')
flags.DEFINE_string('rec_name', '', 'Name of video output of recorded rendering.')
# Camera control
flags.DEFINE_enum('camctl', 'none', ["none", "stop", "erase"], "")
# Light control
flags.DEFINE_enum('lightctl', 'none', ["none", "on", "off", "run", "anim_latlong", "anim_hdri"], "How the sequence should be processed or interpreted by the viewer.")




def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')
    datetime_now = datetime.datetime.now().strftime("%Y%m%d_%H%M")

    # Prepare hardware for tasks
    hw = HW(Cam(), Lights(), Config(os.path.join(FLAGS.cal_folder, FLAGS.cal_name)))
    tib.TIBase.gpu = True
    tib.TIBase.debug = DEBUG

    ### Load image sequence, either by capturing or loading sequence from disk ###
    sequence = None
    if FLAGS.capture:
        # Set name
        seq_name = FLAGS.seq_name if FLAGS.seq_name != '' else datetime_now + '_' + FLAGS.seq_type # 240116_2333_lights

        capture = Capture(hw, FLAGS)
        if not hw.cam.isVideoMode():
            capture.captureSequence(seq_name)
        else:
            capture.captureVideo(seq_name)
        
        
        # Sequence download, evaluation of video not necessary for capture only
        sequence = download(hw, name, keep=FLAGS.sequence_keep, save=FLAGS.sequence_save)
        FLAGS.sequence_name = name
        if FLAGS.capture_mode == 'quick':
            FLAGS.sequence_name+=".MP4"
        
    elif FLAGS.process or FLAGS.viewer:
        # Load from disk
        sequence = load(FLAGS.seq_name, hw.config)
        if len(sequence) == 0:
            log.warning("Empty sequence loaded")
        
            # TODO: Possible scale
        #for id, img in img_seq:
        #    img = img.scale(0.5, False)
        #    img_seq[id] = img

    
    ### Process sequence ###
    renderer = None
    if FLAGS.process:
        tib.TIBase.init()

        settings = dict()
        name = FLAGS.eval_name if FLAGS.eval_name != '' else datetime_now + '_' + FLAGS.eval_type
        match FLAGS.eval_type:
            case 'cal':
                #calibrate(sequence)
                settings = {'interactive': FLAGS.viewer}
                renderer = Calibrate()
                
            case 'rgbstack':
                renderer = RgbStacker()
            case 'lightstack':
                renderer = LightStacker()
            case 'rti':
                settings = {'order': 2}
                renderer = RtiRenderer()
            case 'expostack':
                evalStack(sequence, name)
            case 'convert':
                Convert(sequence, name)
            
        if renderer is not None:
            Process(renderer, sequence, hw.config, name, settings)
            
    ### Launch viewer ###
    if FLAGS.viewer:
        tib.TIBase.init()

        if renderer is None and FLAGS.eval_name != '':
            # Load renderer with eval data
            eval_seq = Sequence()
            eval_seq.load(os.path.join(FLAGS.eval_folder, FLAGS.eval_name))
            renderer = None
            match FLAGS.eval_type:
                case 'rgbstack':
                    renderer = RgbStacker()
                case 'lightstack':
                    renderer = LightStacker()
                case 'rti':
                    renderer = RtiRenderer()
            if renderer is not None:
                renderer.load(eval_seq)
        
        # Launch if renderer is loaded
        if renderer is not None:
            LaunchViewer(renderer)

    ### Config ###
    if type(renderer) is Calibrate:
        # Save config
        cal_name = FLAGS.new_cal_name if FLAGS.new_cal_name != '' else datetime.datetime.now().strftime("%Y%m%d_%H%M") + '_calibration.json' # 240116_2333_calibration.json
        new_cal = renderer.getCalibration()
        log.info(f"Saving calibration as '{cal_name}' with {len(new_cal)} lights from ID {new_cal.getIdBounds()}")
        new_cal.save(FLAGS.cal_folder, cal_name)
        
    ### Camera quick controlls ###
    match FLAGS.camctl:
        case 'none':
            pass
        case 'stop':
            triggerVideoEnd()
        case 'erase':
            # Delete all files on camera
            hw.cam.deleteAll()
        #CamOp.FindMaxExposure(hw.cam)
        #hw.cam.setIso('100')
        #hw.cam.setAperture('8')
        # All done, return
    
    
    ### Light modes after capturing and processing ###
    if FLAGS.lightctl != 'none':
        # Init lights
        hw.lights.getInterface()

        match FLAGS.lightctl:
            case 'on':
                hw.lights.setNth(6, value=100)
                hw.lights.write()
                #lightsTop(hw, brightness=80)
            case 'off':
                hw.lights.off()
            case 'run':
                lightsConfigRun(hw)
            case 'anim_latlong':
                lightsAnimate(hw)
            case 'anim_hdri':
                lightsHdriRotate(hw)

        # Default light
        if FLAGS.lightctl != 'off':
            lightsTop(hw, brightness=80)


                    

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
    if FLAGS.video_safe_rec:
        ids = []
        for id in hw.config.getIds():
            ids.append(id)
            ids.append(id)
    else:
        ids = hw.config.getIds()
    t = Timer(worker.VideoListWorker(hw, ids, subframe_count=1)) # TODO: Subframe count right? Should be FLAGS.video_frames_skip probably?

    # Capture
    hw.cam.triggerVideoStart()
    time.sleep(1)
    t.start((1+FLAGS.video_frames_skip) / FLAGS.video_fps)
    t.join()
    time.sleep(0.5)
    lightsTop(hw, brightness=80)
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


#################### Processing functions ####################

def Process(renderer, img_seq, config, name, settings):
    log.info(f"Process image sequence for {renderer.name}")
        
    # Process
    renderer.process(img_seq, config, settings)

    # Save data
    seq_out = renderer.get()
    if (len(seq_out) > 0):
        domain = seq_out.get(0).domain()
        if not FLAGS.eval_dontsave:
            seq_out.saveSequence(name, FLAGS.eval_folder, ImgFormat.EXR if domain == ImgDomain.Lin else ImgFormat.JPG)


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
        
        path = os.path.join(FLAGS.seq_folder, output_name, f"{output_name}_{id:03d}")
        stacked_seq.append(ImgOp.ExposureStacking(frames, cam_response, path=path), id)
        
        # Save & unload frame
        stacked_seq[id].unload(save=True)
    
    # Return sequence with stacked images       
    return stacked_seq

def Convert(img_seq, output_name):
    for i in range(len(img_seq)):
        img = img_seq.get(i).asDomain(ImgDomain.Lin, as_float=True)
        id = img_seq.getKeys()[i]
        img.setPath(os.path.join(FLAGS.seq_folder, output_name, f"{output_name}_{id:03d}"))
        img.setFormat(ImgFormat.EXR)
        #img = img.scale(0.5) # TODO
        img.unload(save=True)



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


#################### VIEWER ####################

def LaunchViewer(renderer):
    log.info(f"Lauching viewer")
    
    # HDRI
    #hdri = ImgBuffer(os.path.join(FLAGS.hdri_folder, FLAGS.hdri_name), domain=ImgDomain.Lin)
    #res_y, res_x = hdri.get().shape[:2]
    #blur_size = int(15*res_y/100)
    #blur_size += 1-blur_size%2 # Make it odd
    #hdri.set(cv.GaussianBlur(hdri.get(), (blur_size, blur_size), -1))
    
    viewer = Viewer()
    #viewer.setSequences(rti_factors=img_seq)
    #viewer.setHdris([hdri])
    viewer.setRenderer(renderer)
    viewer.launch()
    


#################### CAMERA SETTINGS & DOWNLOAD HELPERS ####################

def download(hw, name, keep=False, save=False):
    """Download from camera"""
    log.debug(f"Downloading sequence '{name}' to {FLAGS.seq_folder}")
    sequence = Sequence()
    if hw.cam.isVideoMode():
        sequence = hw.cam.getVideoSequence(FLAGS.seq_folder, name, hw.config.getIds(), keep=keep)
    else:
        sequence = hw.cam.getSequence(FLAGS.seq_folder, name, keep=keep)
        img_format = ImgFormat.EXR if FLAGS.hdr else ImgFormat.JPG
        if save:
            for _, img in sequence:
                img.save(img_format)
    return sequence
    
def load(seq_name, config):
    """Load from disk"""
    sequence = Sequence()
    
    # TODO: Metadata?
    if seq_name != '':
        path = os.path.join(FLAGS.seq_folder, seq_name)
        if os.path.splitext(seq_name)[1] == '':
            # Load folder
            domain = ImgDomain.Keep
            # Override domain
            match FLAGS.seq_domain:
                case 'lin':
                    domain = ImgDomain.Lin
                case 'srgb':
                    domain = ImgDomain.sRGB
            sequence.loadFolder(path, domain)
        else:
            # Load video
            # IDs according sequence type
            match FLAGS.seq_type:
                case 'lights':
                    ids = config.getIds()
                case 'hdri':
                    ids = [0, 1, 2]
                case 'fullrun':
                    ids = range(512)
            frames_skip = FLAGS.vid_frames_skip * 2 + 1 if FLAGS.vid_safe else FLAGS.vid_frames_skip
            sequence.loadVideo(path, ids, video_frames_skip=frames_skip)
    
    return sequence


#################### MODES END ####################

if __name__ == '__main__':
    app.run(main)
