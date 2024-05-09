import logging as log
from math import radians

# HW & data
from ..hw import *
from ..data import *
# Processes
from . import worker
from .timer import Timer
from .lightctl import LightCtl
from .calibrate import Calibrate
from ..processing.exposureblend import ExpoBlender

class Capture:
    def __init__(self, hw, cal, config):
        self._hw = hw
        self._cam = hw.cam
        self._cal = cal
        self._config = config
        self._lgtctl = LightCtl(hw)
        self._id_list = []
        self._hdr_capture = GetSetting(self._config, 'hdr_capture', False, dtype=bool)

        # Init lights
        hw.lights.getInterface()

        # Generate preview frame
        nth = 4 # TODO
        if self._cal is not None:
            self._preview = [id for id, light in self._cal if light.getLL()[0] > radians(45) and light.getLL()[0] < radians(60)]
        else:
            self._preview = list(range(0, config['capture_max_addr'], step=nth))

    def captureSequence(self, calibration: Calibration = None, hdri: ImgBuffer = None):
        # Get frames for all capture modes
        lights = None
        match self._config['seq_type']:
            case 'lights':
                lights = calibration.getIds()
                self._id_list = lights
            case 'all':
                lights = list(range(self._config['capture_max_addr']))
                self._id_list = lights
            case 'baked':
                self._lgtctl.processHdri(hdri)
                self._lgtctl.sampleHdri(0)
                lights = self._lgtctl.getLights() # Would like to get sth like [{1: 10, 5:100}, {1: 50, 5:80}, {1: 100, 5:30}]
                self._id_list = range(3)

        if not self._cam.isVideoMode():
            self.capturePhotos(lights)
        else:
            self.captureVideo(lights)
        
        
    def capturePhotos(self, lights):
        # Set configuration for camera
        if self._hdr_capture:
            self._cam.setImgFormat(CamImgFormat.Raw)
        else:
            self._cam.setImgFormat(CamImgFormat.JpgMedium)
        
        log.info(f"Starting image capture for {len(self._id_list)} frames")
        # TODO self._id_list is a hack to let worker know how many frames / what IDs to use when a dict/HDRI is used
        t = Timer(worker.LightWorker(self._hw, lights, self._id_list, self._preview, trigger_capture=True, repeat_dmx=self._config['capture_dmx_repeat']))
        t.start(0)
        t.join()
        
        # Default light
        self._lgtctl.setTop(brightness=50)


    def captureVideo(self, lights, trigger_start=True):
        log.info(f"Starting video capture for {len(self._id_list)} frames")
        # Settings
        # Get exposure base and check if value is valid camera entry
        exposure_base = GetSetting(self._config, 'capture_exposure', CamConfigExposure[1/200])
        if not exposure_base in CamConfigExposure.values(): exposure_base = CamConfigExposure[1/200]
        
        # Bracketing number and exposure list
        hdr_captures = self._config['hdr_bracket_num'] if self._hdr_capture else 1
        stops_decrease = int(GetSetting(self._config, 'hdr_bracket_stops', 2))
        for expo_index, expo in enumerate(CamConfigExposure):
            if CamConfigExposure[expo] == exposure_base:
                self._hdr_exposures = [list(CamConfigExposure.keys())[int(expo_index + 3 * i*stops_decrease)] for i in range(hdr_captures)] # 1/3 stop steps in config
                break

        # Worker & Timer
        # Half a subframe for recording + odd number of half skip frames, add another one for each dmx repeat
        subframes = (1+self._config['capture_frames_skip']) // 2 + self._config['capture_dmx_repeat']
        t = Timer(worker.LightVideoWorker(self._hw, lights, self._id_list, self._preview, subframe_count=subframes))
        # Set base exposure
        self._cam.setExposure(exposure_base)

        # Start capture
        if trigger_start:
            self._cam.triggerVideoStart()
            time.sleep(0.5)
        for i in range(hdr_captures):
            t.start(2/self._config['capture_fps'])
            t.join()
            if self._hdr_capture and i < hdr_captures-1:
                self._cam.setExposure(CamConfigExposure[self._hdr_exposures[i+1]])
            time.sleep(0.5)

        self._lgtctl.setTop(brightness=50)
        self._cam.triggerVideoEnd()


    ### Downloading captured data ###

    def downloadSequence(self, name, keep=False):
        """Downloads sequence from camera"""
        log.debug(f"Downloading sequence '{name}' to {self._config['seq_folder']}")

        sequence = Sequence()
        if self._cam.isVideoMode():
            # For HDR, download single sequence and convert those to separate sequences to perform exposure bracketing
            if self._hdr_capture:
                expo_list = [CamConfigExposure[expo] for expo in self._hdr_exposures]
                # Load first sequence
                sequences = [self._cam.getVideoSequence(self._config['seq_folder'], name, self._id_list, exposure_list=expo_list, config=self._config, keep=keep)\
                    .convertSequence({'resolution': (1920, 1080)})]
                # Continue loading others from last sequence
                for i in range(1, self._config['hdr_bracket_num']):
                    sequences.append(Sequence.ContinueVideoSequence(sequences[i-1], os.path.join(self._config['seq_folder'], name+f"_{i}"), self._id_list, i)\
                        .convertSequence({'resolution': (1920, 1080)}))

                # Get exposure times and merge
                exposure_times = [1/float(expo.split("/")[1]) for expo in sequences[0].getMeta('exposures')]
                blender = ExpoBlender()
                blender.process(sequences, self._cal, {'exposure': exposure_times})
                sequence = blender.get()

                # Delete video file maybe? TODO
                
            # For SDR sequence, download video file
            else:
                sequence = self._cam.getVideoSequence(self._config['seq_folder'], name, self._id_list, config=self._config, keep=keep)
        else:
            sequence = self._cam.getSequence(self._config['seq_folder'], name, keep=keep)
        
        return sequence

