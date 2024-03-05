import logging as log

# HW
from src.camera import *
from src.lights import Lights
from src.config import Config
# Timer and worker
from src.timer import Timer, Worker
import src.worker as worker
# Other stuff
from src.imgdata import *
from src.sequence import Sequence
from src.lightdome import Lightdome
from src.calibrate import Calibrate


class Capture:
    def __init__(self, hw, flags):
        self._hw = hw
        self._cam = hw.cam
        self._flags = flags
        self._dome = Lightdome(hw)
        self._id_list = []

        # Init lights
        hw.lights.getInterface()

        # Generate mask frame
        nth = 6
        self._mask_frame = [light['id'] for i, light in enumerate(hw.config) if i % nth == 0]

    def captureSequence(self, config: Config = None, hdri: ImgBuffer = None):
        # Get frames for all capture modes
        if self._flags.seq_type == 'lights':
            lights = config.getIds()
            self._id_list = lights
        elif self._flags.seq_type == 'fullrun':
            lights = range(self._flags.capture_max_addr)
            self._id_list = lights
        elif self._flags.seq_type == 'hdri':
            self._dome.processHdri(hdri)
            self._dome.sampleHdri(0)
            lights = self._dome.getLights() # Would like to get sth like [{1: 10, 5:100}, {1: 50, 5:80}, {1: 100, 5:30}]
            self._id_list = range(3)

        if not self._cam.isVideoMode():
            self.capturePhotos(lights)
        else:
            self.captureVideo(lights)
        
        
    def capturePhotos(self, lights):
        # Set configuration for camera
        if self._flags.hdr:
            self._cam.setImgFormat(CamImgFormat.Raw)
        else:
            self._cam.setImgFormat(CamImgFormat.JpgMedium)
        
        log.info(f"Starting image capture for {len(self._id_list)} frames")
        # TODO self._id_list is a hack to let worker know how many frames / what IDs to use when a dict/HDRI is used
        t = Timer(worker.LightWorker(self._hw, lights, self._id_list, self._mask_frame, trigger_capture=True, repeat_dmx=self._flags.capture_dmx_repeat))
        t.start(0)
        t.join()
        
        # Default light
        self._dome.setTop(brightness=50)


    def captureVideo(self, lights, trigger_start=True):
        log.info(f"Starting video capture for {len(self._id_list)} frames")

        # Worker & Timer
        subframes = 1 + self._flags.capture_frames_skip + self._flags.capture_dmx_repeat
        t = Timer(worker.LightVideoWorker(self._hw, lights, self._id_list, self._mask_frame, subframe_count=subframes))

        # Capture
        if trigger_start:
            self._cam.triggerVideoStart()
            time.sleep(1)
        t.start(2/self._flags.capture_fps)
        t.join()
        time.sleep(0.5)
        self._dome.setTop(brightness=50)
        self._cam.triggerVideoEnd()


    ### Downloading captured data ###

    def downloadSequence(self, name, keep=False, save=False):
        """Downloads sequence from camera"""
        log.debug(f"Downloading sequence '{name}' to {self._flags.seq_folder}")

        sequence = Sequence()
        if self._cam.isVideoMode():
             # TODO: Empty images in sequence
            sequence = self._cam.getVideoSequence(self._flags.seq_folder, name, self._id_list, self._flags.capture_frames_skip*2+1, self._flags.capture_dmx_repeat*2, keep=keep)

            if self._flags.seq_convert:
                sequence.saveSequence(name, self._flags.seq_folder, ImgFormat.JPG)
        else:
            sequence = self._cam.getSequence(self._flags.seq_folder, name, keep=keep)
            if save:
                sequence.saveSequence(name, self._flags.seq_folder, ImgFormat.EXR if self._flags.hdr else ImgFormat.JPG)
        
        return sequence

