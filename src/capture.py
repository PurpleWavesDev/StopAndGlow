class Capture:
    def __init__(self, hw, flags):
        self._cam = hw.cam
        self._lights = hw.lights
        self._flags = flags

        # Init lights
        self._lights.getInterface()
        
    def captureSequence(self, name):
        # Set configuration for camera
        if self._flags.hdr:
            self._cam.setImgFormat(CamImgFormat.Raw)
        else:
            self._cam.setImgFormat(CamImgFormat.JpgMedium)
            
        # Capturing for all modes
        if self._flags.seq_type == 'hdri':
            self.captureHdri()
        elif self._flags.seq_type == 'fullrun':
            capture()
        else: # lights
            #lights
        
        # Default light
        lightsTop(hw, brightness=80)
        
        # Sequence download, evaluation of video not necessary for capture only
        sequence = download(hw, name, keep=FLAGS.sequence_keep, save=FLAGS.sequence_save)
        FLAGS.sequence_name = name
        if FLAGS.capture_mode == 'quick':
            FLAGS.sequence_name+=".MP4"



    def captureVideo(self, name):
        pass