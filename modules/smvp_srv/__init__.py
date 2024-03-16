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
from .camera import *
from .lights import Lights
from .config import Config
from .timer import Timer
from .worker import *
# Image and dome data, evaluation
from .imgdata import *
from .sequence import Sequence
from .capture import Capture
from .lightdome import Lightdome
from .calibrate import Calibrate
from .img_op import *
from .cam_op import *
from .viewer import *
from . import ti_base as tib
# Renderer
from .renderer.renderer import Renderer
from .renderer.rti import RtiRenderer
from .renderer.rgbstack import RgbStacker
from .renderer.lightstack import LightStacker
from .renderer.live import LiveView
from .renderer.exposureblend import ExpoBlender

# Types
HW = namedtuple("HW", ["cam", "lights", "config"])

# Globals
FLAGS = None
DEBUG = hasattr(sys, 'gettrace') and sys.gettrace() is not None


def main(argv):
    # Init logger
    reload(log)
    log.basicConfig(level=log._nameToLevel[FLAGS.loglevel], format='[%(levelname)s] %(message)s')
    datetime_now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    # Make capture_frames_skip odd, increment if necessary
    if FLAGS.capture_frames_skip % 2 == 0:
        FLAGS.capture_frames_skip += 1
    # Prepare hardware for tasks
    hw = HW(Cam(), Lights(), Config(os.path.join(FLAGS.cal_folder, FLAGS.cal_name)))
    tib.TIBase.gpu = True
    tib.TIBase.debug = DEBUG
    tib.TIBase.init()
    
    ### Load image sequence, either by capturing or loading sequence from disk ###
    sequence = None
    if FLAGS.capture:
        # Set name
        ghosting_sequence = Sequence()
        ghosting_sequence.loadFolder(os.path.join(FLAGS.seq_folder, "ghosting"))
        i = len(ghosting_sequence)
        #path=FLAGS.seq_folder
        #for f in os.listdir(path):
        #    p = os.path.join(path, f)
        #    if os.path.isfile(p) and os.path.splitext(p)[1].lower() == '.mp4':
        #        # Load video
        #        sequence = Sequence()
        #        sequence.load(p, frame_list=(0,1), frames_skip=FLAGS.capture_frames_skip, dmx_repeat=FLAGS.capture_dmx_repeat)
        #        frame = sequence.get(0)
        #        frame.setPath(os.path.join(FLAGS.seq_folder, "ghosting", f"ghosting_{i:04d}.jpg"))
        #        frame.save(ImgFormat.JPG)
        #        ghosting_sequence.append(frame, i)
        #        i+=1

        live_renderer = LiveView(hw) # TODO Den gibts noch nicht! Schau in die Renderer (Calibrate, RTI) und bau dir deinen eigenen :)
        live_renderer.setSequence(ghosting_sequence)
        viewer = Viewer((1920,1080))
        viewer.setRenderer(live_renderer)
        viewer.launch()
        while True:
            datetime_now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            FLAGS.seq_name = datetime_now + '_' + FLAGS.seq_type

            capture = Capture(hw, FLAGS)
            hdri = None
            if FLAGS.seq_type == 'hdri':
                # Load hdri
                hdri = ImgBuffer(path=os.path.join(FLAGS.hdri_folder, FLAGS.hdri_name), domain=ImgDomain.Lin)
            capture.captureSequence(hw.config, hdri)
            
            # Sequence download, evaluation of video not necessary for capture only
            sequence = capture.downloadSequence(FLAGS.seq_name, keep=False, save=FLAGS.seq_save)
            # Mask frame for ghosting
            frame = sequence.get(0)
            frame.setPath(os.path.join(FLAGS.seq_folder, "ghosting", f"ghosting_{i:04d}.jpg"))
            frame.save(ImgFormat.JPG)
            ghosting_sequence.append(frame, i)
            i += 1

            live_renderer = LiveView(hw) # TODO Den gibts noch nicht! Schau in die Renderer (Calibrate, RTI) und bau dir deinen eigenen :)
            live_renderer.setSequence(ghosting_sequence)
            viewer = Viewer((1920,1080))
            viewer.setRenderer(live_renderer)
            viewer.launch()



    # If not captured, load sequences
    elif FLAGS.process or FLAGS.viewer:
        # Load from disk
        sequence = load(FLAGS.seq_name, hw.config)
        if len(sequence) == 0:
            log.warning("Empty sequence loaded")

        # For HDR Videos, convert to single sequence
        elif FLAGS.hdr and sequence._is_video:
            # Load first video completely and scale
            sequence.loadFrames()
            if True: #self._flags.video_downscale:
                sequence.convertSequence('hd')
            # Load other sequences from same video file
            sequences = [sequence]
            sequences[0].setMeta('exposure', f"1/50") # TODO
            for i in range(1, FLAGS.hdr_bracket_num):
                sequences.append(Sequence.ContinueVideoSequence(sequences[i-1], os.path.join(FLAGS.seq_folder, FLAGS.seq_name+f"_{i}"), sequence.getKeys(), i))
                sequences[i].setMeta('exposure', f"1/{[50, 200, 800][i]}") # TODO
                # Scale images
                if True: #self._flags.video_downscale:
                    sequences[i].convertSequence('hd')

            # Get exposure times and merge
            exposure_times = [1/float(seq.getMeta('exposure').split("/")[1]) for seq in sequences]
            blender = ExpoBlender()
            blender.process(sequences, hw.config, {'exposure': exposure_times})
            sequence = blender.get()

        # Save videos?
        if FLAGS.seq_convert:
            sequence.saveSequence(FLAGS.seq_name, FLAGS.seq_folder)
    
    ### Process sequence ###
    renderer = None
    if FLAGS.process:
        settings = dict()
        name = FLAGS.eval_name if FLAGS.eval_name != '' else FLAGS.seq_name + '_' + FLAGS.eval_type
        match FLAGS.eval_type:
            case 'cal':
                #calibrate(sequence)
                settings = {'interactive': FLAGS.viewer}
                renderer = Calibrate()
            case 'calstack':
                # Load configs
                stack_cals = [Config(os.path.join(FLAGS.cal_folder, cal_name)) for cal_name in FLAGS.cal_stack_names]
                hw.config.stitch(stack_cals)
                hw.config.save(FLAGS.cal_folder, FLAGS.new_cal_name)
            case 'rgbstack':
                renderer = RgbStacker()
            case 'lightstack':
                renderer = LightStacker()
            case 'rti':
                settings = {'order': 4}
                renderer = RtiRenderer()
            case 'expostack':
                evalStack(sequence, name)
            case 'convert':
                sequence.convertSequence(FLAGS.convert_to)
                sequence.saveSequence(name, FLAGS.seq_folder)
            
        if renderer is not None:
            Process(renderer, sequence, hw.config, name, settings)
            
    ### Launch viewer ###
    if FLAGS.viewer:
        if FLAGS.live:
            live_renderer = LiveView(hw) # TODO Den gibts noch nicht! Schau in die Renderer (Calibrate, RTI) und bau dir deinen eigenen :)
            live_renderer.setSequence(sequence)
            viewer = Viewer((1920,1080))
            viewer.setRenderer(live_renderer)
            viewer.launch()

        elif renderer is None and FLAGS.eval_name != '':
            # Load renderer with eval data
            eval_seq = Sequence()
            eval_seq.load(os.path.join(FLAGS.eval_folder, FLAGS.eval_name))
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
            hw.cam.triggerVideoEnd()
        case 'erase':
            # Delete all files on camera
            hw.cam.deleteAll()
        #CamOp.FindMaxExposure(hw.cam)
        #hw.cam.setIso('100')
        #hw.cam.setAperture('8')
    
    
    ### Light modes after capturing and processing ###
    if FLAGS.lightctl != 'none':
        # Init lights and dome
        hw.lights.getInterface()
        dome = Lightdome(hw)

        match FLAGS.lightctl:
            case 'on':
                dome.setNth(6, 50)
            case 'top':
                dome.setTop(60, 50)
            case 'off':
                hw.lights.off()
            case 'run':
                ids = hw.config.getIds() if FLAGS.seq_type == "seq_type" else range(FLAGS.capture_max_addr)
                lightsRun(hw, ids)
                dome.setTop(60, 50)
            case 'anim_latlong':
                lightsAnimate(hw)
                dome.setTop(60, 50)
            case 'anim_hdri':
                lightsHdriRotate(hw)
                dome.setTop(60, 50)

    # Default lights after image capture
    elif FLAGS.capture and FLAGS.lightctl == 'none':
        Lightdome(hw).setTop(60, 50)
        hw.lights.write()



#################### Light MODES ####################

def lightsAnimate(hw):
    # Function for
    dome = Lightdome(hw)
    def fn_lat(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleWithLatLong(lambda latlong: ImgBuffer.FromPix(50) if latlong[0] > 90-(i*2) else ImgBuffer.FromPix(0))
        dome.writeLights()
        return i<70 # i<45
    def fn_long(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleWithLatLong(lambda latlong: ImgBuffer.FromPix(80 * max(0, 1 - (i*8-latlong[1])/90)) if latlong[1] < i*8 else ImgBuffer.FromPix(0))
        dome.writeLights()
        return i<70 # i<45

    for _ in range(3):
        t = Timer(LightFnWorker(hw, fn_lat, parameter=dome))
        t.start(1/10)
        t.join()

        t = Timer(LightFnWorker(hw, fn_long, parameter=dome))
        t.start(1/10)
        t.join()

def lightsHdriRotate(hw):
    dome = Lightdome(hw)
    hdri = ImgBuffer(os.path.join(FLAGS.hdri_folder, FLAGS.hdri_name), domain=ImgDomain.Lin)
    dome.processHdri(hdri)
    dome.sampleHdri(0)
    img = dome.generateLatLongMapping(hdri)
    ImgOp.SaveEval(img.get(), "hdri_latlong")
    img = dome.generateUVMapping()
    ImgOp.SaveEval(img.get(), "hdri_uv")
    
    # Function for
    def fn(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleHdri(i*3) # 10 degree / second
        dome.writeLights()
        return i<360
    
    t = Timer(LightFnWorker(hw, fn, parameter=dome))
    t.start(1/10)
    t.join()


def lightsRun(hw, ids=None):
    if ids is None:
        ids = hw.config.getIds()
    log.info(f"Running through {len(ids)} lights with IDs {ids[0]}-{ids[-1]}")
    t = Timer(LightWorker(hw, hw.config.getIds()))
    t.start(2/25) # 1/20 is max with occational overruns
    t.join()


#################### Processing functions ####################

def Process(renderer, img_seq, config, name, settings):
    log.info(f"Process image sequence for {renderer.name}")
        
    # Process
    renderer.process(img_seq, config, settings)

    # Save data
    seq_out = renderer.get()
    if (len(seq_out) > 0):
        if not FLAGS.eval_dontsave:
            domain = seq_out.get(0).domain()
            seq_out.saveSequence(name, FLAGS.eval_folder, ImgFormat.EXR if domain == ImgDomain.Lin else ImgFormat.JPG)


def evalStack(sequences, output_name, cam_response=None):
    stacked_seq = Sequence()
    sequence_count = len(sequences)
            
    if False: #cam_response is None:
        # List of current frames
        frames = [seq.getMaskFrame() for seq in sequences]
        cam_response = ImgOp.CameraResponse(frames) # TODO Stuck
        for i in range(len(frames)):
            frames[i].setPath(os.path.join(FLAGS.seq_folder, output_name, f"mask_{i:03d}"))
            frames[i].save(ImgFormat.JPG)
    
    # Iterate over frames
    for i in range(len(sequences[0])):
        # List of current frames
        frames = [seq.get(i) for seq in sequences]
        id = sequences[0].getKeys()[i]
                
        if cam_response is None:
            cam_response = ImgOp.CameraResponse(frames) # TODO Stuck
            for i in range(len(frames)):
                frames[i].setPath(os.path.join(FLAGS.seq_folder, output_name, f"first_{i:03d}"))
                frames[i].save(ImgFormat.JPG)
        
        path = os.path.join(FLAGS.seq_folder, output_name, f"{output_name}_{id:03d}")
        stacked_seq.append(ImgOp.ExposureStacking(frames, cam_response, path=path), id)
        
        # Save & unload frame
        stacked_seq[id].unload(save=True)
    
    # Return sequence with stacked images       
    return stacked_seq



#################### RELIGHT MODES ####################

def relightSimple(img_seq, config, output_name):
    # Deine Funktion, Iris :)
    log.info(f"Generate HDRI Lighting from Sequence")

    dome = Lightdome(config)
    hdri = ImgBuffer(os.path.join(FLAGS.seq_folder, FLAGS.input_hdri), domain=ImgDomain.Lin)
    dome.processHdri(hdri)

    # Sequence generator
    for i in range(72):
        lighting = dome.generateLightingFromSequence(img_seq, longitude_offset=i*5)
        lighting.setPath(os.path.join(FLAGS.seq_folder, output_name, f"{output_name}_{i:03d}"))
        lighting.set(lighting.get()*40)
        lighting = lighting.asDomain(ImgDomain.sRGB)
        lighting.setFormat(ImgFormat.JPG)
        lighting.save()
        
    return
    # Generate scene with HDRI lighting 
    lighting = dome.generateLightingFromSequence(img_seq, longitude_offset=FLAGS.hdri_rotation)

    lighting.setPath(os.path.join(FLAGS.seq_folder, output_name, output_name))
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
    
def load(seq_name, config):
    """Load from disk"""
    sequence = Sequence()
    
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
                    ids = range(FLAGS.capture_max_addr)
            # TODO: Video parameters via metadata?
            sequence.load(path, ids, FLAGS.capture_frames_skip, FLAGS.capture_dmx_repeat) 
    
    return sequence


#################### MODES END ####################

if __name__ == '__main__':
    app.run(main)
