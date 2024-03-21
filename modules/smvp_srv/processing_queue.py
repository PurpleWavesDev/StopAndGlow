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
from .process import *


class ProcessingQueue:
    def __init__(self):
        self._worker = Worker()
        
        self._queue = multiprocessing.Queue(20)
            
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
        self._sock = {}
        self._context = zmq.Context()
                
    def addConsumer(self, address_string):
        # Open new socket to consumer
        address_str = f"tcp://{address_string}"
        self._sock[address_string] = self._context.socket(zmq.PUSH)
        self._sock[address_string].connect(address_str)
                        
    def work(self, queue, keep_running):
        self._keep_running = keep_running
        
        # Setup hardware
        self._hw = HW(Cam(), Lights(), Calibration('../HdM_BA/data/calibration/lightdome.json')) # Calibration(os.path.join(FLAGS.cal_folder, FLAGS.cal_name)
        self._lightctl = LightCtl(self._hw)
        
        # Capture data
        self._capture = CaptureData()

        while self._keep_running or not queue.empty():
            try:
                command, arg, settings = queue.get_nowait()
                self.processCommand(command, arg, settings)
            except Q.Empty:
                time.sleep(0.1)
            except Exception as e:
                log.error(f"Error processing command: {str(e)}")
            
            
    def processCommand(self, command, arg, settings):
        match command:
            case Commands.Config:
                pass
            
            case Commands.Capture:
                pass
            
            case Commands.Load:
                pass
            
            case Commands.Convert:
                pass
            
            case Commands.Process:
                pass
            
            case Commands.Render:
                pass
            
            case Commands.View:
                pass
            
            case Commands.Save:
                pass
            
            case Commands.Send:
                # --send address:port id=1 mode=render|preview|live
                if not arg in self._sock:
                    self.addConsumer(arg)
                
                id = GetVal(settings, 'id', 0)
                mode = GetVal(settings, 'mode', 'preview')
                if mode == 'render':
                    send_array(self._sock[arg], id, self._capture.render.get())
                elif mode == 'preview':
                    send_array(self._sock[arg], id, self._capture.preview.get())
                elif mode == 'live':
                    send_array(self._sock[arg], id, self._hw.cam.capturePreview().rescale((1920, 1080)).asFloat().getWithAlpha())
                
            case Commands.Lights:
                # --lights on value=50 range=0.2
                match arg:
                    case 'on'|'rand':
                        self._lightctl.setNth(6, 50)
                    case 'top':
                        self._lightctl.setTop(60, 50)
                    case 'off':
                        self._hw.lights.off()
                
            case Commands.Sleep:
                # --sleep 1.0
                time.sleep(float(arg))
            
            case Commands.Quit:
                log.debug("Processing worker quit command received")
                self._keep_running = False
                return
            
            case _:
                log.error(f"Unknown command '{command}'")

def GetVal(d, key, default=None):
    if key in d:
        return d[key]
    return default