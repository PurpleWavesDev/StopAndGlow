import multiprocessing
import queue as Q
from threading import Thread
import logging as log
import time
import zmq

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


class ProcessingQueue:
    def __init__(self, context=None):
        self._worker = Worker(context)
        self._queue = multiprocessing.Queue(255)
            
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
        self._queue.put((Commands.Quit, ""))
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
        self.if_stack = []
        # Setup Taichi
        tib.TIBase.gpu = True #false fürs surface
        tib.TIBase.debug = True #false fürs surface
        tib.TIBase.init()
        
        # Default config
        self.config = Config()
        
        # Sequence data and buffers
        self.sequence = Sequence()
        self.hdri = ImgBuffer(path=os.path.join(self.config['hdri_folder'], self.config['hdri_name'])) # TODO: Default HDRI?
        self.img_buf = ImgBuffer.CreateEmpty(self.config['resolution'], True)
        self.path = ""
        
        # Setup hardware
        self.cal = Calibration(path=os.path.join(self.config['cal_folder'], self.config['cal_name']))
        self.hw = HW(Cam(), Lights())
        self.lightctl = LightCtl(self.hw, self.cal)
                
        # Rendering
        self.renderer = Renderer(BSDF(), self.config['resolution'])

        while self._keep_running or not queue.empty():
            try:
                command, arg, settings = queue.get_nowait()
                if len(self.if_stack) > 0 and command == Commands.EndIf:
                    self.if_stack.pop()
                elif len(self.if_stack) == 0 or self.if_stack[-1]:
                    self.processCommand(command, arg, settings)
            except Q.Empty:
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
                log.info(f"Processing '--config {arg}' ...")
                
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
                    # TODO: get?
                    case 'save':
                        self.config.save(path)
                    case _:
                        raise Exception(f"Unknown argument '{arg}' for --config command, use load/set/save")
            
            
            case Commands.Calibration:
                # --calibration load name=cal.json folder=/jada/jada
                log.info(f"Processing '--calibration {arg}' ...")
                
                folder = GetSetting(settings, 'folder', self.config['cal_folder'])
                match arg:
                    case 'load':
                        name = GetSetting(settings, 'name', self.config['cal_name'])
                        path = os.path.join(folder, name)
                        if os.path.isfile(path):
                            self.cal.load(path)
                            print(f"Loaded calibration file with {len(self.cal)} lights")
                        else:
                            raise Exception(f"File {path} does not exist")
                    case 'save':
                        name = GetSetting(settings, 'name', GetDatetimeNow()+'.json')
                        path = os.path.join(folder, name)
                        self.cal.save(path)
                    case _:
                        raise Exception(f"Unknown argument '{arg}' for --calibration command, use load/save")

            
            case Commands.Preview:
                # --preview live/baked
                log.info(f"Capturing preview '{arg}'")
                
                settings = self.config.get() | settings
                if arg == 'live':
                    self.img_buf = self.hw.cam.capturePreview()
                elif arg == 'baked': # TODO: Capture with camera preview
                    capture = Capture(self.hw, self.cal, settings)
                    capture.captureSequence(self.cal, self.hdri)
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
                capture = Capture(self.hw, self.cal, settings)
                capture.captureSequence(self.cal, self.hdri)
                # Download
                if arg != 'baked':
                    self.sequence = capture.downloadSequence(name, keep=False)
                else:
                    # TODO!
                    baked_seq = capture.downloadSequence(name, keep=False)
                    stacked = self.process(baked_seq, 'rgbstack', {})
                    self.sequence.setDataSequence('baked', stacked)
            
            
            case Commands.Load:
                # --load <path> seq_type=<lights,baked,all>
                # Check if sequence is already loaded
                # TODO: keep n sequences in memory (?)
                if not self.path == arg:
                    self.path = arg
                    
                    log.info(f"Loading sequence '{arg}'")
                    
                    # Is argument absolute path or relative to seq_folder?
                    if not os.path.exists(self.path):
                        self.path = os.path.join(self.config['seq_folder'], arg)
                        if not os.path.exists(self.path):
                            raise Exception(f"File/folder '{arg}' not found")
                
                    # Get config and frame list for video files
                    default_config = self.config.get()
                    if os.path.splitext(self.path)[1] != '':
                        # Video file, add IDs to defaults according to sequence type
                        match GetSetting(settings, 'seq_type', 'lights'):
                            case 'lights':
                                ids = self.cal.getIds()
                            case 'baked':
                                ids = [0, 1, 2]
                            case 'all':
                                ids = list(range(config['capture_max_addr']))
                        # Assign IDs to default config
                        default_config['video_frame_list'] = ids
                    
                    # Replace sequence and load
                    self.sequence = Sequence()
                    self.sequence.load(self.path, defaults=default_config, overrides=settings)

            case Commands.LoadHdri:
                # --loadHdri <path> folder=<path> rotation=0
                log.info(f"Loading HDRI '{arg}'")
                
                # Is argument absolute path or relative to hdri_folder?
                path = arg
                if 'folder' in settings or not os.path.isfile(path):
                    path = os.path.join(GetSetting(settings, 'folder', self.config['hdri_folder']), arg)
                    if not os.path.isfile(path):
                        raise Exception(f"File '{arg}' not found")
                
                # Load file
                rotation = float(GetSetting(settings, 'rotation', '0'))
                self.hdri = ImgBuffer(path)
            
            
            case Commands.Calibrate:
                # --calibrate calc/interactive/merge threshold=245 min_size_ratio=0.011 calibrations=cal1,cal2,cal3 folder=path
                log.info(f"Starting calibration '{arg}'")
                if 'focal_length' in settings: self.sequence.setMeta('focal_length', int(GetSetting(settings, 'focal_length')))
                
                if arg == 'calc':
                    processor = Calibrate()
                    processor.setSequence(self.sequence)
                    processor.process()
                    self.cal = processor.getCalibration()
                elif arg == 'interactive':
                    # Init GUI and Viewer
                    resolution = (int(self.config['resolution'][0]), int(self.config['resolution'][1]))
                    gui = GUI(resolution)
                    viewer = Calibrate()
                    viewer.setSequence(self.sequence)
                    viewer.process(settings, interactive=True)
                    gui.setViewer(viewer)
                    
                    # Launch
                    gui.launch()
                    # Assign new calibration
                    self.cal = viewer.getCalibration()
                    
                elif arg == 'merge':
                    folder = GetSetting(settings, 'folder', self.config['cal_folder'])
                    new_cals = [Calibration(os.path.join(folder, cal_name)) for cal_name in GetSetting(settings, 'calibrations', '').split(',')]
                    self.cal.align(new_cals)
                    self.cal = self.cal.getMerged(new_cals)
                
                 
            case Commands.Process:
                # --process <type> setting=value
                #exists = arg in self.sequence.getDataKeys() if GetSetting(settings, 'destination', 'data') == 'data' else 
                #if not arg in self.sequence.getDataKeys() or GetSetting(settings, 'override', False):
                log.info(f"Processing sequence with '{arg}'")
                self.sequence = self.process(self.sequence, arg, settings)
                
            
            case Commands.Render:
                match arg:
                    case 'config':
                        if 'algorithm' in settings:
                            algo_key = GetSetting(settings, 'algorithm')
                            if algo_key in algorithms:
                                log.info(f"Render configuration with algorithm '{algo_key}'")
                                name, _, algo_settings = algorithms[algo_key]
                                bsdf_class, bsdf_settings = bsdfs[algo_settings['bsdf']]
                                bsdf = bsdf_class()
                                if bsdf.load(self.sequence, self.cal, algo_key, bsdf_settings):
                                    self.renderer = Renderer(bsdf, self.config['resolution'])
                                    # Set HDRI
                                    if self.hdri.get() is not None:
                                        self.renderer.getScene().setHdri(self.hdri)
                                else:
                                    log.error("Can't load BSDF data!")
                            else:
                                log.error(f"Render configuration with bsdf '{algo_key}'")
                    case 'reset':
                        self.renderer.reset()
                    case 'light':
                        self.renderer.getScene().addLight(settings)
                    case 'canvas':
                        pass # TODO: Transform vom Canvas-Objekt hinzufügen
                    case 'hdri':
                        pass
                    case 'hdri_data':
                        pass
                    case 'render':
                        self.renderer.initRender()
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
                        viewer = RenderViewer()
                        viewer.setRenderer(self.renderer)
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
                # --save all/sequence/data name=<name> basepath=<basepath>
                log.info(f"Saving sequences '{arg}'")
                
                # Name and path
                name = GetSetting(settings, 'name', self.sequence.name())
                path = GetSetting(settings, 'basepath')
                format = GetSetting(settings, 'format', 'exr').lower()
                if path is None:
                    path = os.path.normpath(self.sequence.directory())
                else:
                    path = os.path.normpath(os.path.join(path, name))
            
                # Save sequences
                if arg == 'all' or arg == 'sequence':
                    # path: Parent of sequence directory -> joined with name is same directory again
                    self.sequence.saveSequence(name, os.path.dirname(path), ImgFormat.EXR if format == 'exr' else ImgFormat.JPG)
                if arg == 'all' or arg == 'data':
                    for key in self.sequence.getDataKeys():
                        self.sequence.getDataSequence(key).saveSequence(key, path, ImgFormat.EXR if format == 'exr' else ImgFormat.JPG)
                
            case Commands.Send:
                # --send address:port id=1 mode=render|baked|preview|live
                if self._consumer is None:
                    self.setConsumer(arg)
                
                id = GetSetting(settings, 'id', 0)
                mode = GetSetting(settings, 'mode', 'preview')
                resolution = self.config['resolution']
                try:
                    depth = self.sequence.getDataSequence('depth')[0].r().get()
                except:
                    depth = None
                
                if mode == 'preview':
                    preview = self.sequence.getPreview()
                    if preview.resolution() != resolution:
                        # Scale to current resolution
                        preview.set(preview.rescale(resolution, crop=True).asDomain(ImgDomain.Lin).withAlpha(depth).get())
                    self.sendImg(id, preview.get())
                elif mode == 'baked':
                    self.sendImg(id, self.baked.withAlpha().get())
                elif mode == 'render':
                    rendered = ImgBuffer(img=self.renderer.get())
                    self.sendImg(id, rendered.withAlpha(depth).get())
                elif mode == 'live':
                    preview = self.hw.cam.capturePreview()
                    self.sendImg(id, preview.rescale(resolution, crop=True).asFloat().withAlpha().get())
            
            
            case Commands.Lights:
                # --lights on power=0.5 range=0.2
                log.info(f"Set Lights to '{arg}'")
                
                power = min(float(GetSetting(settings, 'power', 1/3)), 1.0)
                amount = min(float(GetSetting(settings, 'amount', 1/3)), 1.0)
                width = min(float(GetSetting(settings, 'width', 1/5)), 1.0)

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
            
            
            case Commands.If:
                # --if valid/empty/length/meta_valid/meta_empty/meta_compare sequence=frames/preview data=path greater=10 equals=5 inequals=stuff less=3 metakey=key metaval=val
                compare_seq = self.sequence
                is_preview = False
                compare_op = '='
                compare_val = "0"
                meta_key = ''
                
                for cmd, val in settings.items():
                    match cmd:
                        case 'sequence':
                            is_preview = True if val == 'preview' else False
                        case 'data':
                            compare_seq = self.sequence.getDataSequence(val)
                        case 'equals':
                            compare_val = val
                            compare_op = '='
                        case 'inequals':
                            compare_val = val
                            compare_op = '!'
                        case 'greater':
                            compare_val = val
                            compare_op = '>'
                        case 'less':
                            compare_val = val
                            compare_op = '<'
                        case 'metakey':
                            meta_key = val
                        case 'metaval':
                            meta_val = val
                
                match arg:
                    case 'valid':
                        if is_preview:
                            evaluated = compare_seq.getPreview().get() != None
                        else:
                            evaluated = len(compare_seq) > 0
                    case 'empty':
                        if is_preview:
                            evaluated = compare_seq.getPreview().get() == None
                        else:
                            evaluated = len(compare_seq) == 0
                    case 'length':
                        match compare_op:
                            case '=':
                                evaluated = len(compare_seq) == int(compare_val)
                            case '!':
                                evaluated = len(compare_seq) != int(compare_val)
                            case '>':
                                evaluated = len(compare_seq) > int(compare_val)
                            case '<':
                                evaluated = len(compare_seq) < int(compare_val)
                    case 'meta_valid':
                        evaluated = compare_seq.getMeta(meta_key) != None
                    case 'meta_empty':
                        evaluated = compare_seq.getMeta(meta_key) == None
                    case 'meta_compare':
                        m = compare_seq.getMeta(meta_key)
                        if m != None:
                            match compare_op: # TODO string/int/float ? 
                                case '=':
                                    evaluated = m == compare_val
                                case '!':
                                    evaluated = m != compare_val
                                case '>':
                                    evaluated = int(m) > int(compare_val)
                                case '<':
                                    evaluated = int(m) < int(compare_val)
                        else:
                            log.warnin(f"Can't compare invalid key '{meta_key}' in meta_compare statement, defaulting to False")
                            evaluated = False
                    case _:
                        log.error(f"Invalid argument '{arg}' for if command, use valid/empty/length/meta_valid/meta_empty/meta_compare")
                
                self.if_stack.append(evaluated)
                log.info(f"if '{arg}' command evaluated to {evaluated}")
                
            case Commands.EndIf:
                log.error("No matching if for endif command")

            
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
        seq_name = arg
        
        match arg:
            case 'fitting':
                # Apply settings from fitter list
                seq_name = settings['fitter']
                _, fitter, fitter_settings = algorithms[seq_name]
                processor = fitter()
                settings = settings | fitter_settings
            case 'generate':
                seq_name = settings['generator']
                _, generator, generator_settings = generators[seq_name]
                processor = generator()
                settings = settings | generator_settings
            case 'convert':
                self.sequence.convertSequence(settings)
            case DepthEstimator.name:
                processor = DepthEstimator()
            case ExpoBlender.name:
                processor = ExpoBlender()
            case RgbStacker.name:
                processor = RgbStacker()
            case RtiProcessor.name:
                processor = RtiProcessor()
            case LightstackProcessor.name:
                processor = LightstackProcessor()
            case _:
                log.error(f"Unknown processor type '{arg}'")
        
        # Processing
        if processor is not None:
            target = GetSetting(settings, 'target', 'sequence')
            match target:
                case 'sequence':
                    processor.process(img_seq, self.cal, settings)
                    
                    if GetSetting(settings, 'destination') == 'alpha':
                        for id, processed in processor.get():
                            img_seq[id] = img_seq[id].withAlpha(processed.get())
                    
                case 'preview':
                    preview_seq = Sequence()
                    preview_seq.append(img_seq.getPreview(), 0)
                    processor.process(preview_seq, self.cal, settings)
                    
                    if GetSetting(settings, 'destination') == 'alpha':
                        img_seq.setPreview(img_seq.getPreview().withAlpha(processor.get()[0].get()))
                case _:
                    log.warning(f"Processing target '{target}' not implemented")
                    
            # Set data
            data_seq = processor.get()
            if GetSetting(settings, 'destination', 'data') == 'data':
                if len(data_seq) > 0:
                    img_seq.setDataSequence(seq_name, data_seq)
        return img_seq

    
    def sendImg(self, id, img):
        send_array(self._consumer, id, img)
        answer = receive(self._consumer)
        if answer.command != Command.RecvOkay:
            if answer.command == Command.RecvError:
                log.error(f"Received error while sending image data: {answer.data['message']}")

