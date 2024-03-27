import multiprocessing
import queue as Q
from threading import Thread
import logging as log
import time
import zmq
from datetime import datetime

from smvp_ipc import *

from .commands import *
from .hw import *
from .data import *
from .procedure import *
from .render import *
from .utils import ti_base as tib
from .engine import *


class ProcessingQueue:
    def __init__(self):
        self._worker = Worker()
        
        self._queue = multiprocessing.Queue(50)
            
    def putCommand(self, command: Commands, arg, settings={}):
        self._queue.put((command, arg, settings))
    
    def launch(self):
        self._process = Thread(target=Worker.work, args=(self._worker, self._queue, True,))
        self._process.start()
        
    def run(self):
        """Process filled queue without launching a separate process"""
        self._worker.work(self._queue, False)
        
    def stop(self):
        self._queue.put(Commands.Quit, "")
        self._process.join()
        
        

class Worker:
    def __init__(self, send_results=False):
        # Setup processing queue
        self._consumer = None
        self._context = zmq.Context()
                
    def setConsumer(self, address_string):
        # Open new socket to consumer
        address_str = f"tcp://{address_string}"
        self._consumer = self._context.socket(zmq.PUSH)
        self._consumer.connect(address_str)
                        
    def work(self, queue, keep_running):
        self._keep_running = keep_running
        # Setup Taichi
        tib.TIBase.gpu = True
        tib.TIBase.debug = True
        tib.TIBase.init()
        self.tib_buffer = None
        
        # Default config
        self.config = Config()
        
        # Sequence data and buffers
        self.sequence = Sequence()
        self.render = ImgBuffer()
        self.preview = ImgBuffer()
        self.baked = ImgBuffer()
        self.hdri = ImgBuffer(path=os.path.join(self.config['hdri_folder'], self.config['hdri_name']))
        
        # Setup hardware
        calibration = Calibration(path=os.path.join(self.config['cal_folder'], self.config['cal_name']))
        self.hw = HW(Cam(), Lights(), calibration)
        self.lightctl = LightCtl(self.hw)
        self.executor = None
        self.id

        while self._keep_running or not queue.empty():
            try:
                command, arg, settings = queue.get_nowait()
                self.processCommand(command, arg, settings)
            except Q.Empty:
                if self.executor is not None:
                    self.sendImage(self.id)
                else:
                    time.sleep(0.1)
            except Exception as e:
                log.error(f"Error processing command: {str(e)}")
            
            
    def processCommand(self, command, arg, settings):
        match command:
            case Commands.Config:
                # --config load path=/bla/bla name=config.json
                # --config set key=value
                if arg == 'load':
                    # TODO
                    GetSetting(settings, 'path', '')
                    #self.config = Config(path)
                elif arg == 'set':
                    for key, val in settings.items():
                        self.config[key] = val
            
            case Commands.Capture:
                # --capture lights
                # Name and settings
                name = GetSetting(settings, 'name', GetDatetimeNow())
                settings = self.config.get() | settings
                settings['seq_type'] = arg
                
                # Create capture object and capture
                capture = Capture(self.hw, settings)
                capture.captureSequence(self.hw.cal, self.hdri)
                # Download
                if arg != 'hdri': #TODO: Should HDRI be a separate sequence or set as data sequence?
                    self.sequence = capture.downloadSequence(name, keep=False)
                else:
                    hdri_seq = capture.downloadSequence(name, keep=False)
                    stacked = self.process(hdri_seq, 'rgbstack', {})
                    self.baked = stacked[0]
                    #self.sequence.setDataSequence()
                
            case Commands.Load:
                # --load <path> seq_type=<lights,hdri,fullrun>
                default_config = self.config.get()
                if os.path.splitext(arg)[1] != '':
                    # Video file, add IDs to defaults according to sequence type
                    match GetSetting(settings, 'seq_type', 'lights'):
                        case 'lights':
                            ids = calibration.getIds()
                        case 'hdri':
                            ids = [0, 1, 2]
                        case 'fullrun':
                            ids = range(config['capture_max_addr'])
                    default_config = {**default_config, **{'video_frame_list', ids}}
                
                # Replace sequence and load
                self.sequence = Sequence()
                self.sequence.load(arg, defaults=default_config, overrides=settings)
                
                # Get preview
                self.preview = self.sequence.getPreview().asDomain(ImgDomain.sRGB, ti_buffer=self.tib_buffer)
                res = self.config['resolution']
                scale = max(res[0] / self.preview.resolution()[0], res[1] / self.preview.resolution()[1])
                self.preview = self.preview.scale(scale).crop(res)
            
            
            case Commands.Convert:
                # --convert size=4k|hd format=??
                self.sequence.convertSequence(settings)
            
            case Commands.Process:
                data_sequence = self.process(self.sequence, arg, settings)
                if data_sequence is not None:
                    self.sequence.setDataSequence(data_key, data_sequence)
            
            case Commands.Render:
                pass
            
            case Commands.View:
                pass
            
            case Commands.Save:
                self.sequence.saveSequence(name, FLAGS.seq_folder)
            
            case Commands.Send:
                # --send address:port id=1 mode=render|baked|preview|live
                if self._consumer is None:
                    self.setConsumer(arg)
                
                id = GetSetting(settings, 'id', 0)
                mode = GetSetting(settings, 'mode', 'preview')
                self.executor = None
                if mode == 'preview':
                    send_array(self._consumer, id, self.preview.getWithAlpha())
                elif mode == 'baked':
                    send_array(self._consumer, id, self.baked.getWithAlpha())
                elif mode == 'render':
                    send_array(self._consumer, id, self.render.getWithAlpha())
                elif mode == 'live':
                    self.id = id
                    self.executor = Engine(self.hw, self.config['resolution'], EngineModes.Live)
                    self.sendImage(id)
                
            case Commands.Lights:
                # --lights on power=0.5 range=0.2
                power = min(GetSetting(settings, 'power', 1/3), 1.0)
                amount = min(GetSetting(settings, 'amount', 1/3), 1.0)
                width = min(GetSetting(settings, 'width', 1/6), 1.0)

                match arg:
                    case 'on'|'rand':
                        self.lightctl.setNth(round(1/amount), int(power*255))
                    case 'top':
                        self.lightctl.setTop(90-90*amount, int(power*255))
                    case 'ring':
                        self.lightctl.setRing(90-90*amount, 90*width, int(power*255))
                    case 'off':
                        self.hw.lights.off()
                
            case Commands.Sleep:
                # --sleep 1.0
                time.sleep(float(arg))
            
            case Commands.Quit:
                log.debug("Processing worker quit command received")
                self._keep_running = False
                return
            
            case _:
                log.error(f"Unknown command '{command}'")
    
    
    def process(self, img_seq, arg, settings):
        # --process <type> setting=value
        # Get renderer
        renderer = None
        data_sequence = None
        data_key = ""
        
        match arg:
            case 'cal':
                if not interactive in settings: settings['interactive'] = True
                renderer = Calibrate()
            case 'calstack':
                #stack_cals = [Calibration(os.path.join(FLAGS.cal_folder, cal_name)) for cal_name in FLAGS.cal_stack_names]
                #self.hw.cal.stitch(stack_cals)
                #self.hw.cal.save(FLAGS.cal_folder, FLAGS.new_cal_name)
                pass
            case 'rgbstack':
                renderer = RgbStacker()
            case 'lightstack':
                renderer = LightStacker()
            case 'depth':
                renderer = DepthEstimator()
            case 'rti':
                if not order in settings: settings['order'] = 4
                renderer = RtiRenderer()     

            case _:
                log.error(f"Unknwon processor type '{arg}'")
        
        # Process renderers
        if renderer is not None:
            log.info(f"Process image sequence for {renderer.name}")                    
            # Process
            renderer.process(img_seq, calibration, settings)
            # Store data
            if len(renderer.get()) > 0:
                data_sequence = renderer.get()
                data_key = renderer.name_short
        
        return data_sequence
    
    def sendImage(self, id):
        send_array(self._consumer, id, self.executor.execute().getWithAlpha())


### Helper ###

def GetDatetimeNow():
    return datetime.now().strftime("%Y%m%d_%H%M")
