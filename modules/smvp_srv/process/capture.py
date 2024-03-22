import logging as log

# HW & data
from ..hw import *
from ..data import *
# Processes
from . import worker
from .timer import Timer
from .lightctl import LightCtl
from .calibrate import Calibrate
from ..render.exposureblend import ExpoBlender

class Capture:
    def __init__(self, hw, config):
        self._hw = hw
        self._cam = hw.cam
        self._config = config
        self._lgtctl = LightCtl(hw)
        self._id_list = []

        # Init lights
        hw.lights.getInterface()

        # Generate preview frame
        nth = 4 # TODO
        if hw.cal is not None:
            self._preview = [light['id'] for i, light in enumerate(hw.cal) if light['latlong'][0] > 45 and light['latlong'][0] < 60]
        else:
            self._preview = list(range(0, config['capture_max_addr'], step=nth))

    def captureSequence(self, calibration: Calibration = None, hdri: ImgBuffer = None):
        # Get frames for all capture modes
        lights = None
        match self._config['seq_type']:
            case 'lights':
                lights = calibration.getIds()
                self._id_list = lights
            case 'fullrun':
                lights = list(range(self._config['capture_max_addr']))
                self._id_list = lights
            case 'hdri':
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
        if self._config['hdr_capture']:
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
        base_exposure = 50 # TODO: {int(base_exposure * stops_increase**i)} Must match camera setting, maybe try to find closest setting in camera config
        stops_increase = self._config['hdr_bracket_stops']
        hdr_captures = self._config['hdr_bracket_num'] if self._config['hdr_capture'] else 1
        self._hdr_exposures = [50, 200, 800] # TODO

        # Worker & Timer
        # Half a subframe for recording + odd number of half skip frames, add another one for each dmx repeat
        subframes = (1+self._config['capture_frames_skip']) / 2 + self._config['capture_dmx_repeat']
        t = Timer(worker.LightVideoWorker(self._hw, lights, self._id_list, self._preview, subframe_count=subframes))
        if self._config['hdr_capture']:
            self._cam.setExposure(f"1/{self._hdr_exposures[0]}")

        # Start capture
        if trigger_start:
            self._cam.triggerVideoStart()
            time.sleep(0.5)
        for i in range(hdr_captures):
            t.start(2/self._config['capture_fps'])
            t.join()
            if self._config['hdr_capture'] and i < hdr_captures-1:
                self._cam.setExposure(f"1/{self._hdr_exposures[i+1]}")
            time.sleep(0.5)

        self._lgtctl.setTop(brightness=50)
        self._cam.triggerVideoEnd()


    ### Downloading captured data ###

    def downloadSequence(self, name, keep=False):
        """Downloads sequence from camera"""
        log.debug(f"Downloading sequence '{name}' to {self._config['seq_folder']}")

        sequence = Sequence()
        if self._cam.isVideoMode():
            # For HDR, download all sequences with sequence number attached and convert those to a single merged EXR sequence
            if self._config['hdr_capture']:
                expo_list = [f"1/{expo}" for expo in self._hdr_exposures]
                sequences = [(self._cam.getVideoSequence(self._config['seq_folder'], name, self._id_list, self._config['capture_frames_skip'], self._config['capture_dmx_repeat'], exposure_list=expo_list, keep=keep))]
                
                for i in range(1, self._config['hdr_bracket_num']):
                    sequences.append(Sequence.ContinueVideoSequence(sequences[i-1], os.path.join(self._config['seq_folder'], name+f"_{i}"), self._id_list, i))

                # Only scale images, will write out as EXRs anyway
                if True: # seq_downscale:
                    for seq in sequences:
                        seq.convertSequence({'size': 'hd'})

                # Get exposure times and merge
                exposure_times = [1/float(seq.getMeta('exposure').split("/")[1]) for seq in sequences]
                blender = ExpoBlender()
                blender.process(sequences, self._hw.cal, {'exposure': exposure_times})
                sequence = blender.get()

            
            # For SDR sequence, download video file
            else:
                sequence = self._cam.getVideoSequence(self._config['seq_folder'], name, self._id_list, self._config['capture_frames_skip'], self._config['capture_dmx_repeat'], keep=keep)
        else:
            sequence = self._cam.getSequence(self._config['seq_folder'], name, keep=keep)
        
        return sequence

