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
from .processing import *
from .render import *
from .viewer import *
from .utils import ti_base as tib
from .utils.utils import GetDatetimeNow

from .engine import *


class ProcessingQueue:
    def __init__(self, context=None):
        self._worker = Worker(context)
        self._queue = multiprocessing.Queue(50)
            
    def putCommand(self, command: Commands, arg, settings={}):
        self._queue.put((command, arg, settings))
        
    def getConfig(self):
        return self._worker.getConfig()
    
    def launch(self):
        self._process = Thread(target=Worker.work, args=(self._worker, self._queue, True,))
        self._process.start()
        
    def execute(self):
        """Process filled queue without launching a separate process"""
        self._worker.work(self._queue, False)
        
    def quit(self):
        self._queue.put(Commands.Quit, "")
        self._process.join()
        
        

class Worker:
    def __init__(self, context=None):
        # Setup processing queue
        self.config = None
        self._consumer = None
        self._context = context if context is not None else zmq.Context()
                
    def getConfig(self):
        return self.config
                        
    def work(self, queue, keep_running) -> bool:
        self._keep_running = keep_running
        # Setup Taichi
        tib.TIBase.gpu = True
        tib.TIBase.debug = True
        tib.TIBase.init()
        
        # Default config
        self.config = Config()
        
        # Sequence data and buffers
        self.sequence = Sequence()
        self.hdri = ImgBuffer(path=os.path.join(self.config['hdri_folder'], self.config['hdri_name']))
        self.img_buf = ImgBuffer.CreateEmpty(self.config['resolution'], True)
        
        # Setup hardware
        calibration = Calibration(path=os.path.join(self.config['cal_folder'], self.config['cal_name']))
        self.hw = HW(Cam(), Lights(), calibration)
        self.lightctl = LightCtl(self.hw)
        
        # For client communication and continuous execution
        self.req_id = 0
        self.executor = None
        
        # Rendering
        self.renderer = Renderer()
        #self.ti_buffer = ti.ndarray(ti.types.vector(3, ti.f32), (self.config['resolution'][1], self.config['resolution'][0])) # Cannot loop over the object <class 'taichi.lang.matrix.VectorNdarray'> in Taichi scope. Only Taichi fields (via template) or dense arrays (via types.ndarray) are supported.
        self.ti_buffer = ti.field(tib.pixvec)
        ti.root.dense(ti.ij, (self.config['resolution'][1], self.config['resolution'][0])).place(self.ti_buffer)
        self.ti_buffer.from_numpy(self.img_buf.get())
        self.ti_buffer.to_numpy()

        while self._keep_running or not queue.empty():
            try:
                command, arg, settings = queue.get_nowait()
                self.processCommand(command, arg, settings)
            except Q.Empty:
                if self.executor is not None:
                    self.sendImage(self.req_id)
                else:
                    time.sleep(0.1)
            except Exception as e:
                log.error(f" Command '{command} {arg}': {str(e)}")
                if not self._keep_running:
                    return False
        
        # Delete important buffers explicitly to allow them to save all data
        # Otherwise, open() can be deleted before destructors can make use of the function (python bug)
        del self.sequence
        del self.hw
        del self.config
        
        return True
            
            
    def processCommand(self, command, arg, settings):
        match command:
            case Commands.Config:
                # --config load folder=/bla/bla name=config.json
                # --config set key=value
                # --config save name=newconf.json
                log.info(f"Processing '--config {arg}'...")
                
                path = GetSetting(settings, 'folder', self.config['config_folder'])
                name = GetSetting(settings, 'name', self.config['config_name'])
                match arg:
                    case 'load':
                        path = os.path.join(path, name)
                        if os.path.isfile(path):
                            self.config = Config(path)
                        else:
                            raise Exception(f"File {path} does not exist")
                    case 'set':
                        for key, val in settings.items():
                            self.config[key] = val
                    case 'save':
                        self.config.save(path)
                    case _:
                        raise Exception(f"Unknown argument '{arg}' for --config command, use load/set/save")
            
            
            case Commands.Calibration:
                # --calibration load name=cal.json folder=/jada/jada
                log.info(f"Processing '--calibration {arg}'...")
                
                path = GetSetting(settings, 'folder', self.config['cal_folder'])
                name = GetSetting(settings, 'name', self.config['cal_name'])
                match arg:
                    case 'load':
                        path = os.path.join(path, name)
                        if os.path.isfile(path):
                            calibration = Calibration(path)
                            self.hw.cal._replace(cal=calibration)
                        else:
                            raise Exception(f"File {path} does not exist")
                    case 'save':
                        self.hw.cal.save(path)
                    case _:
                        raise Exception(f"Unknown argument '{arg}' for --calibration command, use load/save")

            
            case Commands.Preview:
                # --preview live/baked
                log.info(f"Capturing preview '{arg}'")
                
                settings = self.config.get() | settings
                if arg == 'live':
                    self.img_buf = self.hw.cam.capturePreview()
                elif arg == 'baked':
                    capture = Capture(self.hw, settings)
                    capture.captureSequence(self.hw.cal, self.hdri)
                    baked_seq = capture.downloadSequence(name, keep=False)
                    self.img_buf = self.process(baked_seq, 'rgbstack', {})[0]
                else:
                    raise Exception(f"Unknown argument '{arg}' for --preview command, use live/baked")


            case Commands.Capture:
                # --capture lights
                log.info(f"Capturing sequence '{arg}'")
                
                if not arg in ['lights', 'all', 'baked']:
                    raise Exception(f"Unknown argument '{arg}' for --capture command, use lights/all/baked")
                
                # Name and settings
                name = GetSetting(settings, 'name', GetDatetimeNow()+f"_{arg}", default_for_empty=True)
                settings = self.config.get() | settings
                settings['seq_type'] = arg
                
                # Create capture object and capture
                capture = Capture(self.hw, settings)
                capture.captureSequence(self.hw.cal, self.hdri)
                # Download
                if arg != 'baked':
                    self.sequence = capture.downloadSequence(name, keep=False)
                else:
                    baked_seq = capture.downloadSequence(name, keep=False)
                    stacked = self.process(baked_seq, 'rgbstack', {})
                    self.sequence.setDataSequence('baked', stacked)
            
            
            case Commands.Load:
                # --load <path> seq_type=<lights,baked,all>
                log.info(f"Loading sequence '{arg}'")
                
                # Is argument absolute path or relative to seq_folder?
                path = arg
                if not os.path.exists(path):
                    path = os.path.join(self.config['seq_folder'], arg)
                    if not os.path.exists(path):
                        raise Exception(f"File/folder '{arg}' not found")
                
                # Get config and frame list for video files
                default_config = self.config.get()
                if os.path.splitext(path)[1] != '':
                    # Video file, add IDs to defaults according to sequence type
                    match GetSetting(settings, 'seq_type', 'lights'):
                        case 'lights':
                            ids = calibration.getIds()
                        case 'baked':
                            ids = [0, 1, 2]
                        case 'all':
                            ids = range(config['capture_max_addr'])
                    default_config = {**default_config, **{'video_frame_list', ids}}
                
                # Replace sequence and load
                self.sequence = Sequence()
                self.sequence.load(path, defaults=default_config, overrides=settings)
                
                # Get preview TODO
                self.preview = self.sequence.getPreview().asDomain(ImgDomain.sRGB, ti_buffer=self.ti_buffer)
                res = self.config['resolution']
                scale = max(res[0] / self.preview.resolution()[0], res[1] / self.preview.resolution()[1])
                self.preview = self.preview.scale(scale).crop(res)


            case Commands.LoadHdri:
                # --loadHdri <path>
                log.info(f"Loading HDRI '{arg}'")
                
                # Is argument absolute path or relative to hdri_folder?
                path = arg
                if not os.path.isfile(path):
                    path = os.path.join(self.config['hdri_folder'], arg)
                    if not os.path.isfile(path):
                        raise Exception(f"File '{arg}' not found")
                
                # Load file
                self.hdri = ImgBuffer(path)
            
            
            case Commands.Calibrate:
                # --calibrate new/stack? setting=value
                log.info(f"Starting calibration '{arg}'")
                # TODO!
                if arg == 'calc':
                    processor = Calibrate()
                elif arg == 'interactive':
                    if not interactive in settings: settings['interactive'] = True
                    processor = Calibrate()
                elif arg == 'stack':
                    stack_cals = [Calibration(os.path.join(FLAGS.cal_folder, cal_name)) for cal_name in FLAGS.cal_stack_names]
                    self.hw.cal.stitch(stack_cals)
                    self.hw.cal.save(FLAGS.cal_folder, FLAGS.new_cal_name)
                
                 
            case Commands.Process:
                # --process <type> setting=value
                log.info(f"Processing sequence with '{arg}'")
                
                self.sequence = self.process(self.sequence, arg, settings)
                
            
            case Commands.Render:
                match arg:
                    case 'config':
                        if 'algorithm' in settings:
                            bsdf = [bsdf for name, _, bsdf in bsdfs if name == settings['algorithm']]
                            if len(bsdf) == 1:
                                bsdf = bsdf[0]()
                                bsdf.load(self.sequence, self.hw.cal) # TODO: What if sequence has no bsdf data?
                                self.renderer.setBsdf(bsdf)
                    case 'reset':
                        self.renderer.getScene().clear()
                    case 'light':
                        self.renderer.getScene().addLight(settings)
                    case 'hdri':
                        pass
                    case 'hdri_data':
                        pass
                    case 'render':
                        self.renderer.initRender(self.ti_buffer)
                        self.renderer.sample() # TODO
            
            case Commands.View:
                # --view sequence/render/preview/live
                log.info(f"Launching viewer for '{arg}'")
                
                resolution = (int(self.config['resolution'][0]), int(self.config['resolution'][1]))
                gui = GUI(resolution)
                viewer = None
                match arg: # TODO: Not all Viewers implemented!
                    case 'sequence':
                        viewer = SequenceViewer()
                        viewer.setSequence(self.sequence)
                    case 'render':
                        pass
                    case 'preview':
                        pass
                    case 'live':
                        viewer = LiveViewer(self.hw)
                    case _:
                        raise Exception(f"Unknown argument '{arg}' for --view command, use sequence/render/preview/live")
                
                # Launch GUI
                gui.setViewer(viewer)
                gui.launch()
            
            case Commands.Save:
                # --save <path>
                log.info(f"Saving sequence as '{arg}'")
                
                # Abspath?
                if os.path.isabs(arg):
                    self.sequence.saveSequence(os.path.basename(arg), os.path.dirname(arg))
                else:
                    self.sequence.saveSequence(arg, self.config['seq_folder'])
            
            case Commands.Send:
                # --send address:port id=1 mode=render|baked|preview|live
                if self._consumer is None:
                    self.setConsumer(arg)
                
                id = GetSetting(settings, 'id', 0)
                mode = GetSetting(settings, 'mode', 'preview')
                self.executor = None
                if mode == 'preview':
                    self.sendImg(id, self.sequence.getPreview().withAlpha().get())
                elif mode == 'baked':
                    self.sendImg(id, self.baked.withAlpha().get())
                elif mode == 'render':
                    # TODO: Straight from buffer? Alpha channel?
                    rendered = ImgBuffer(img=self.ti_buffer.to_numpy())
                    self.sendImg(id, rendered.withAlpha().get())
                elif mode == 'live':
                    self.req_id = id
                    self.executor = Engine(self.hw, self.config['resolution'], EngineModes.Live)
                    self.sendImage(id)
            
            
            case Commands.Lights:
                # --lights on power=0.5 range=0.2
                log.info(f"Set Lights to '{arg}'")
                
                power = min(GetSetting(settings, 'power', 1/3), 1.0)
                amount = min(GetSetting(settings, 'amount', 1/3), 1.0)
                width = min(GetSetting(settings, 'width', 1/5), 1.0)

                match arg:
                    case 'on'|'rand':
                        if amount != 0:
                            self.lightctl.setNth(round(1/amount), int(power*255))
                        else:
                            self.hw.lights.off()
                    case 'top':
                        self.lightctl.setTop(90-90*amount, int(power*255))
                    case 'ring':
                        self.lightctl.setRing(90-90*amount, 135*width, int(power*255))
                    case 'off':
                        self.hw.lights.off()
            
            case Commands.Camera:
                pass
                
            case Commands.Sleep:
                # --sleep 1.0
                log.info(f"Sleep for {arg}s")
                
                time.sleep(float(arg))
            
            case Commands.Quit:
                log.debug("Processing worker quit command received")
                self._keep_running = False
                return
            
            case _:
                log.error(f"Unknown command '{command}'")
    
    
    def setConsumer(self, address_string):
        # Open new socket to consumer
        address_str = f"tcp://{address_string}"
        self._consumer = self._context.socket(zmq.REQ)
        self._consumer.connect(address_str)
        
    def process(self, img_seq, arg, settings):
        processor = None
        
        match arg:
            case 'convert':
                self.sequence.convertSequence(settings) # TODO
            case DepthEstimator.name:
                processor = DepthEstimator()
            case ExposureBlender.name:
                processor = ExposureBlender()
            case RgbStacker.name:
                processor = RgbStacker()
            case 'rti':
                if not order in settings: settings['order'] = 4
                processor = RtiRenderer()     
            case _:
                log.error(f"Unknwon processor type '{arg}'")
        
        # Processing
        if processor is not None:
            target = GetSetting(settings, 'target', 'sequence')
            match target:
                case 'sequence':
                    processor.process(img_seq, calibration, settings)
                    
                    if GetSetting(settings, 'destination') == 'alpha':
                        for id, processed in processor.get():
                            img_seq[id] = img_seq[id].withAlpha(processed.get())
                    
                case 'preview':
                    preview_seq = Sequence()
                    preview_seq.append(img_seq.getPreview(), 0)
                    processor.process(preview_seq, calibration, settings)
                    
                    if GetSetting(settings, 'destination') == 'alpha':
                        img_seq.setPreview(img_seq.getPreview().withAlpha(processor.get()[0].get()))
                case _:
                    log.warning(f"Processing target '{target}' not implemented")
                    
            # Set data
            data_seq = processor.get()
            if GetSetting(settings, 'destination', 'data') == 'data':
                if len(data_seq) > 0:
                    img_seq.setDataSequence(processor.name, data_seq)
        return img_seq

    
    def sendImage(self, id):
        time.sleep(0.1)
        self.sendImg(id, self.executor.execute().withAlpha().get())

    def sendImg(self, id, img):
        send_array(self._consumer, id, img)
        answer = receive(self._consumer)
        if answer.command != Command.RecvOkay:
            if answer.command == Command.RecvError:
                log.error(f"Received error while sending image data: {answer.data['message']}")

