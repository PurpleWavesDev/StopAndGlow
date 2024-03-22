# Process imports
import subprocess
import signal
import io
import os
import time
import pathlib
import logging as log
from pathlib import Path
from queue import Queue

# Camera & image imports
from PIL import Image
import cv2 as cv
import rawpy
#import exiv2

from ..data import *
from ..utils.utils import logging_disabled
from .camconf_canon90d import *

try:
    import gphoto2 as gp
except:
    log.warning("GPhoto2 not available")

class VideoCapture:
    def __init__(self, camera_file, camera_path, exposure="", aperture="", iso=""):
        self.camera_file = camera_file
        self.camera_path = camera_path
        self.exposure = exposure
        self.aperture = aperture
        self.iso = iso

class Cam:
    def __init__(self):
        # Lets kill any gphoto process that blocks the ressource
        try:
            killgphoto2()
        except:
            pass
        # Lazy loading for camera
        self._cam = None
        self._files = dict()
        self._mask_file = None
        self._video_capture = Queue()

    def __del__(self):
        if self._cam is not None:
            self._cam.exit()
        
    def getCam(self):
        if self._cam is None:
            self._cam = gp.Camera()
            self._cam.init()
        return self._cam

    ### Config methodes ###
    # File format (raw/jpg/heif?), file size/type, ???
    
    def isVideoMode(self) -> bool:
        widget = self.getCam().get_single_config('eosmovieswitch')
        return widget.get_value() == '1'
    
    def setVideoResolution(self, resolution): # TODO
        widget = self.getCam().get_single_config('videoresolution') # Find config parameter
        widget.set_value(widget.get_choice(resolution.value)) # ?
        self.getCam().set_single_config('videoresolution', widget)

    def isRaw(self) -> bool:
        img_format = self.getImgFormat()
        return img_format == CamImgFormat.Raw or img_format == CamImgFormat.cRaw

    def setImgFormat(self, imgFormat: CamImgFormat):
        widget = self.getCam().get_single_config('imageformat')
        widget.set_value(widget.get_choice(imgFormat.value))
        self.getCam().set_single_config('imageformat', widget)

    def getImgFormat(self) -> CamImgFormat:
        widget = self.getCam().get_single_config('imageformat')
        # Find current choice ID
        value = widget.get_value()
        choice_id = -1
        for i in range(widget.count_choices()):
            if value == widget.get_choice(i):
                choice_id = i
                break   
        return CamImgFormat(choice_id)
    
    def setAperture(self, aperture='5.6'):
        widget = self.getCam().get_single_config('aperture')
        widget.set_value(aperture)
        self.getCam().set_single_config('aperture', widget)
    def getAperture(self):
        widget = self.getCam().get_single_config('aperture') # String, e.g. '5.6', type Radio
        return widget.get_value()
        
    def setExposure(self, shutter='1/200'):
        widget = self.getCam().get_single_config('shutterspeed')
        widget.set_value(shutter)
        self.getCam().set_single_config('shutterspeed', widget)
    def getExposure(self):
        widget = self.getCam().get_single_config('shutterspeed') # String, e.g. '1/50', type Radio
        return widget.get_value()

    def setIso(self, iso='200'):
        widget = self.getCam().get_single_config('iso')
        widget.set_value(iso)
        self.getCam().set_single_config('iso', widget)
    def getIso(self):
        widget = self.getCam().get_single_config('iso') # String, e.g. '1000', type Radio
        return widget.get_value()

    # More useful values: colortemperature

    # Read only

    def getBattery(self): # Untested
        widget = self.getCam().get_single_config('batterylevel')
        return widget.get_value()

    ### Capture & Trigger methodes ###

    def waitForVideo(self, timeout=0):
        listen_timeout = timeout*100 if timeout != 0 else 1000
        time_start = time.time()
        while time.time() - time_start < timeout if timeout != 0 else True:
            event_type, event_data = self.getCam().wait_for_event(listen_timeout)      
            if event_type == 0 and event_data == 'PTP Property d1b8 changed, "movierecordtarget" to "Card"':
                # Video captured
                return True
            elif False: # event_type == 0:
                # 0 Button 2 -> focus button (oder button 3/1? Wahrscheinlich unterschiedliche zustände)
                return True

    def waitForPhoto(self, timeout=1000, blocking=False):
        listen_timeout = timeout*1000
        time_start = time.time()
        while time.time() - time_start < timeout if timeout != 0 else True:
            event_type, event_data = self.getCam().wait_for_event(listen_timeout)      
            if event_type == 0 and event_data == '0 Button 2':
                # Video captured
                return True
            if not blocking:
                return False

        #listen_timeout = timeout*1000
        #time_start = time.time()
        #while time.time() - time_start < timeout or timeout == 0:
        #    event_type, event_data = self.getCam().wait_for_event(int(listen_timeout))        
        #    if event_type == gp.GP_EVENT_FILE_ADDED:
        #        sequence = Sequence()
        #        # Load and delete file from camera
        #        img = self.getCam().file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
        #        self.getCam().file_delete(event_data.folder, event_data.name)
        #        # Append and set metadata
        #        sequence.append(img, 0)
        #        sequence.setMeta("exposure", self.getExposure())
        #        sequence.setMeta("aperture", self.getAperture())
        #        sequence.setMeta("iso", self.getIso())
        #        return sequence
        #    elif not blocking:
        #        return None
        #    # Sleep and return to wait for event
        #    sleep(0.1)
    
    def focus(self, steps=1):
        """steps from -3 to +3 to select different step sizes"""
        steps = min(3, max(-3, steps))
        widget = self.getCam().get_single_config('manualfocusdrive')
        if steps < 0:
            widget.set_value(widget.get_choice(abs(steps)-1))
            self.getCam().set_single_config('manualfocusdrive', widget)
        elif steps > 0:
            widget.set_value(widget.get_choice(3+steps))
            self.getCam().set_single_config('manualfocusdrive', widget)
        # TODO: Another 0 value to "apply" settings to allow another step afterwards. Might be necessary depending on the camera?
        widget.set_value(widget.get_choice(3))
        self.getCam().set_single_config('manualfocusdrive', widget)

    def capturePhoto(self, id):
        """Captures image and saves camera file path"""
        file = self.getCam().capture(gp.GP_CAPTURE_IMAGE)
        if id == -1:
            self._mask_file = [file.folder, file.name]
        else:
            self._files[id] = [file.folder, file.name]

    def capturePreview(self) -> ImgBuffer:
        """Captures preview image in a quick way but low resolution"""
        capture = self.getCam().capture_preview()
        filedata = capture.get_data_and_size()
        image = np.array(Image.open(io.BytesIO(filedata)))
        return ImgBuffer(img=image, domain=ImgDomain.sRGB)

    def triggerPhoto(self):
        self.getCam().trigger_capture()
        
    def triggerVideoStart(self):
        widget = self.getCam().get_single_config('viewfinder')
        widget.set_value(1)
        self.getCam().set_single_config('viewfinder', widget)
        widget = self.getCam().get_single_config('movierecordtarget')
        widget.set_value("Card")
        self.getCam().set_single_config('movierecordtarget', widget)

    def triggerVideoEnd(self):
        # Stop recording
        widget = self.getCam().get_single_config('movierecordtarget')
        widget.set_value("None")
        self.getCam().set_single_config('movierecordtarget', widget)
        # Wait for event, timeout 3 sec TODO: Function takes really long in total, blocks lights in bright state
        timeout = 3.0
        time_start = time.time()
        while time.time() - time_start < timeout:
            event_type, event_data = self.getCam().wait_for_event(int(timeout*1000))        
            if event_type == gp.GP_EVENT_FILE_ADDED:
                capture = VideoCapture(self.getCam().file_get(event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL), (event_data.folder, event_data.name))
                capture.exposure = self.getExposure()
                capture.aperture = self.getAperture()
                capture.iso = self.getIso()
                self._video_capture.put(capture)
                break

    ### Image & Download methodes ###
    
    def getImage(self, id, path, name, keep=False) -> ImgBuffer:
        """Downloads a single image by ID from the camera"""
        file = self._files[id] if id != -1 else self._mask_file      
        #file_data = self.getCam().file_get(file[0], file[1], gp.GP_FILE_TYPE_NORMAL).get_data_and_size() # TODO! This fails sometimes
        # Workaround, save image in temp folder
        tmp_path = os.path.join('/tmp', f"{name}_{id:03d}{os.path.splitext(file[1])[1]}")
        self.getCam().file_get(file[0], file[1], gp.GP_FILE_TYPE_NORMAL).save(tmp_path)
        
        # Check for format and domain
        domain = ImgDomain.sRGB
        ext = os.path.splitext(file[1])[1].lower()
        io_bytes = None
        # TODO: Alignment error, doesn not work like this!!
        if ext == '.jpg' or ext == '.jpeg':
            # Open normally
            with logging_disabled():
                io_bytes = open(tmp_path, "rb") # io.BytesIO(file_data) # TODO: Read from file instead from memory bc of bug
                #image = cv.imdecode(np.frombuffer(io_bytes.read(), np.uint8), 1)
                image = np.array(Image.open(io_bytes))
        elif  ext == '.heif' or ext == '.heic':
            log.warn("HEIF full bit depth not implemented yet!")
            with logging_disabled():
                image = np.array(Image.open(io.BytesIO(file_data)))
        else:
            # It's most likely raw! Convert to readable formats
            io_bytes = open(tmp_path, "rb") # io.BytesIO(file_data) # TODO: Read from file instead from memory bc of bug
            #image = cv.imdecode(np.frombuffer(io_bytes.read(), np.uint8), 1)
            domain = ImgDomain.Lin
            image = self.convertRaw(io_bytes)
        
        # Metadata TODO!
        #exiv_image = exiv2.ImageFactory.open(io_bytes)
        #exiv_image.readMetadata()
        #exif_data = exiv_image.exifData()
        #print(exif_data)

        if not keep:
            self.getCam().file_delete(file[0], file[1])
            if id != -1:
                del self._files[id]
            else:
                self._mask_file = None

        # Local full path to image 
        full_path = os.path.join(path, name, f"{name}_{id:03d}{ext}" if id != -1 else f"{name}_mask{ext}")
        return ImgBuffer(path=full_path, img=image, domain=domain)
        
    def getSequence(self, path, name, keep=False, save=False) -> Sequence:
        """Returns all images of the saved paths from the camera as an Sequence sequence"""
        seq = Sequence()
        for id in self._files.keys():
            img = self.getImage(id, path, name, keep=True)
            if save:
                img.save()
            seq.append(img, id)
        if self._mask_file != None:
            img = self.getImage(-1, path, name, keep=True)
            if save:
                img.save()
            seq.setPreview(img)
        if not keep:
            self.deleteFiles()
        
        # Metadata from camera TODO: could be extracted from EXIF per file but settings propably won't change
        seq.setMeta('aperture', self.getAperture())
        seq.setMeta('iso', self.getIso())
        seq.setMeta('exposure', self.getExposure())
        # TODO: Metadata for focal length and sensor size, gphoto does not have interface for that

        return seq
    
    def downloadImages(self, path, name, keep=False):
        """Downloads all images of the saved paths from the camera directly to the file system"""
        for id in self._files.keys():
            self.getImage(id, path, name, keep).unload(save=True)


    def getVideoSequence(self, path, name, frame_list, frames_skip, dmx_repeat, exposure_list=[], keep=False) -> Sequence:
        """Downloads video file and returns sequence referencing it"""
        seq = Sequence()
        if not self._video_capture.empty():
            capture = self._video_capture.get()
            file_path = os.path.join(path, name+os.path.splitext(capture.camera_path[1])[1])
            Path(path).mkdir(parents=True, exist_ok=True)
            log.debug("Video is being saved to {}".format(file_path))
            capture.camera_file.save(file_path)
            seq.load(file_path, frame_list, frames_skip, dmx_repeat)
            seq.setMeta('video_file', file_path)
            seq.setMeta('aperture', capture.aperture)
            seq.setMeta('iso', capture.iso)
            # Set exposure
            if not exposure_list:
                seq.setMeta('exposure', capture.exposure)
            else:
                seq.setMeta(f'exposure', exposure_list[0])
                for i, expo in enumerate(exposure_list):
                    seq.setMeta(f'exposure_{i}', expo)

            if not keep:
                self.getCam().file_delete(capture.camera_path[0], capture.camera_path[1])
        
        return seq


    def listFiles(self, path='/'):
        """Returns list of all files found on the camera"""
        result = []
        # get files
        for name, _ in self.getCam().folder_list_files(path):
            ext = os.path.splitext(filename[1])
            # Only add if file is no video
            if ext.lower() != '.mov' and ext.lower() != '.mp4':
                result.append(os.path.join(path, name))
        
        # Call function recursively for subfolders
        for subfolder, _ in self.getCam().folder_list_folders(path):
            result.extend(self.listFiles(os.path.join(path, subfolder)))

        return result

    def addFiles(self, file_list, start_number=0, id_list=None):
        """Adds files to file list, starting with custom number"""
        if id_list is not None:
            for file, id in zip(file_list, id_list):
                self._files[id] = os.path.split(file)
        else:
            for file in file_list:
                self._files[start_number] = os.path.split(file)
                start_number+=1
                
    def resetFiles(self):
        """Resets internal file list"""
        self._files = dict()

    def deleteFiles(self):
        """Deletes all known files on camera"""
        for id, file in self._files.items():
            self.getCam().file_delete(file[0], file[1])
        self._files = dict()

    def deleteAll(self, path='/'):
        for name, _ in self.getCam().folder_list_files(path):
            self.getCam().file_delete(path, name)
        # Call function recursively for subfolders
        for subfolder, _ in self.getCam().folder_list_folders(path):
            self.deleteAll(os.path.join(path, subfolder))
        


    ### Helper ###
    
    def convertRaw(self, raw_img):
        """Converts raw images to image arrays and returns an image buffer"""
        raw = rawpy.imread(raw_img)
        # Params for post process TODO: Check additional settings https://letmaik.github.io/rawpy/api/rawpy.Params.html
        params = rawpy.Params(output_color=rawpy.ColorSpace.raw, half_size=False, noise_thr=20, gamma=(1,1), no_auto_bright=True, output_bps=16)
        rgb = raw.postprocess(params).astype('float32') / 65536
        
        return rgb



def killgphoto2():
    """Helper to kill the gvfsd-gphoto2 process if camera resource is blocked"""
    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out,err = p.communicate()
    for line in out.splitlines():
        if b'gvfsd-gphoto2' in line:
            #kill process
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)
   
