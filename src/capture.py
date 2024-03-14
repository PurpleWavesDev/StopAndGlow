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
from src.renderer.exposureblend import ExpoBlender

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
        nth = 4
        if hw.config is not None:
            self._mask_frame = [light['id'] for i, light in enumerate(hw.config) if light['latlong'][0] > 45]
        else:
            self._mask_frame = list(range(0, flags.capture_max_addr, step=nth))

    def captureSequence(self, config: Config = None, hdri: ImgBuffer = None):
        # Get frames for all capture modes
        if self._flags.seq_type == 'lights':
            lights = config.getIds()
            self._id_list = lights
        elif self._flags.seq_type == 'fullrun':
            lights = list(range(self._flags.capture_max_addr))
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
        # Settings
        base_exposure = 50 # TODO: {int(base_exposure * stops_increase**i)} Must match camera setting, maybe try to find closest setting in camera config
        stops_increase = self._flags.hdr_bracket_stops
        hdr_captures = self._flags.hdr_bracket_num if self._flags.hdr else 1
        self._hdr_exposures = [50, 200, 800] # TODO

        # Worker & Timer
        # Half a subframe for recording + odd number of half skip frames, add another one for each dmx repeat
        subframes = (1+self._flags.capture_frames_skip) / 2 + self._flags.capture_dmx_repeat
        t = Timer(worker.LightVideoWorker(self._hw, lights, self._id_list, self._mask_frame, subframe_count=subframes))
        if self._flags.hdr:
            self._cam.setExposure(f"1/{self._hdr_exposures[0]}")

        # Start capture
        if trigger_start:
            self._cam.triggerVideoStart()
            time.sleep(0.5)
        for i in range(hdr_captures):
            t.start(2/self._flags.capture_fps)
            t.join()
            if self._flags.hdr and i < hdr_captures-1:
                self._cam.setExposure(f"1/{self._hdr_exposures[i+1]}")
            time.sleep(0.5)

        self._dome.setTop(brightness=50)
        self._cam.triggerVideoEnd()


    ### Downloading captured data ###

    def downloadSequence(self, name, keep=False, save=False):
        """Downloads sequence from camera"""
        log.debug(f"Downloading sequence '{name}' to {self._flags.seq_folder}")

        sequence = Sequence()
        if self._cam.isVideoMode():
            # For HDR, download all sequences with sequence number attached and convert those to a single merged EXR sequence
            if self._flags.hdr:
                expo_list = [f"1/{expo}" for expo in self._hdr_exposures]
                sequences = [(self._cam.getVideoSequence(self._flags.seq_folder, name, self._id_list, self._flags.capture_frames_skip, self._flags.capture_dmx_repeat, exposure_list=expo_list, keep=keep))]
                
                if self._flags.seq_convert:
                    for i in range(1, self._flags.hdr_bracket_num):
                        sequences.append(Sequence.ContinueVideoSequence(sequences[i-1], os.path.join(self._flags.seq_folder, name+f"_{i}"), self._id_list, i))

                    # Only scale images, will write out as EXRs anyway
                    if True: #self._flags.seq_downscale:
                        for seq in sequences:
                            seq.convertSequence('hd')

                    # Get exposure times and merge
                    exposure_times = [1/float(seq.getMeta('exposure').split("/")[1]) for seq in sequences]
                    blender = ExpoBlender()
                    blender.process(sequences, self._hw.config, {'exposure': exposure_times})
                    sequence = blender.get()

                # TODO!
                else:
                    sequence = sequences[0]
            
            # For SDR sequence, download video file
            else:
                sequence = self._cam.getVideoSequence(self._flags.seq_folder, name, self._id_list, self._flags.capture_frames_skip, self._flags.capture_dmx_repeat, keep=keep)

                # Convert if flag is set 
                if self._flags.seq_convert:
                    sequence.convertSequence(self._flags.convert_to)

        else:
            sequence = self._cam.getSequence(self._flags.seq_folder, name, keep=keep)
            if self._flags.seq_convert:
                sequence.convertSequence(self._flags.convert_to)

        # Save sequence
        if False: #save: # TODO
            sequence.saveSequence(name, self._flags.seq_folder)
        
        return sequence

