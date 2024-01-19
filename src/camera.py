# Camera imports
import gphoto2 as gp
from PIL import Image
import rawpy
import imageio
imageio.plugins.freeimage.download()

# Process imports
import subprocess
import signal
import os
import io
import pathlib

from src.imgdata import * 
from src.utils import logging_disabled

class Cam:
    def __init__(self):
        # Lets kill any gphoto process that blocks the ressource
        killgphoto2()
        # Lazy loading for camera
        self._cam = None
        self._files = dict()

    def __del__(self):
        if self._cam is not None:
            self._cam.exit()
        
    def getCam(self):
        if self._cam is None:
            self._cam = gp.Camera()
            self._cam.init()
        return self._cam

    ### Config methodes ###
    # File format (raw/jpg/heif?), file size/type, aperture, exposure time, ???
    
    def setRaw(self, raw=True):
        if raw:
            pass
        else:
            pass
    def isRaw(self) -> bool:
        return False
    
    def setImgType(self, imgType):
        pass
    def getImgType(self):
        return None
    
    def setAperture(self, aperture=5.6):
        pass
    def getAperture(self):
        return 5.6
        
    def setExposure(self, exposure=1/200):
        pass
    def getExposure(self):
        return 1/200

    def setIso(self, iso=200):
        pass
    def getIso(self):
        return 200


    ### Capture & Trigger methodes ###
    
    def capturePhoto(self, id):
        """Captures image and saves camera file path"""
        file = self.getCam().capture(gp.GP_CAPTURE_IMAGE)
        self._files[id] = [file.folder, file.name]

    def capturePreview(self):
        """Captures preview image in a quick way but low resolution"""
        capture = self.getCam().capture_preview()
        filedata = capture.get_data_and_size()
        image = Image.open(io.BytesIO(filedata)) # TODO: Probably doesn't work
        return ImgBuffer(img=image, domain=ImgDomain.sRGB)

    def triggerPhoto(self):
        self.getCam().trigger_capture()
        
    def triggerVideoStart(self):
        self.getCam().set_config(viewfinder=1)
        self.getCam().set_config(movierecordtarget=Card)
        #self.getCam().set_config(gp.GP_CAPTURE_MOVIE)
    def triggerVideoEnd(self):
        self.getCam().set_config(movierecordtarget=None)

        # Wait for event, timeout 2 sec
        timeout = 3000
        time_start = time_now() # TODO
        while time_start - time_now() < timeout:
            event_type, event_data = camera.wait_for_event(timeout)        
            if event_type == gp.GP_EVENT_FILE_ADDED:
                cam_file = camera.file_get(
                    event_data.folder, event_data.name, gp.GP_FILE_TYPE_NORMAL)
                target_path = os.path.join(os.getcwd(), event_data.name)
                print("Image is being saved to {}".format(target_path))
                cam_file.save(target_path)

    ### Image & Download methodes ###
    
    def getImage(self, id, path, name, keep=False) -> ImgBuffer:
        """Downloads a single image by ID from the camera"""
        file = self._files[id]        
        file_data = self.getCam().file_get(file[0], file[1], gp.GP_FILE_TYPE_NORMAL).get_data_and_size()
        # Check for format and domain
        domain = ImgDomain.sRGB
        ext = os.path.splitext(file[1])[1].lower()
        if ext != '.jpg' and ext != '.jpeg' and ext != '.heif' and ext != '.heic':
            # It's most likely raw! Convert to readable formats
            domain = ImgDomain.Lin
            image = self.convertRaw(image)
        else:
            # Open normally
            # TODO: Alignment error, doesn not work like this!!
            with logging_disabled():
                image = Image.open(io.BytesIO(file_data))
        
        if not keep:
            self.getCam().file_delete(file[0], file[1])
            del self._files[id]

        # Local full path to image 
        full_path = os.path.join(path, name, f"{name}_{id:03d}{ext}")
        return ImgBuffer(path=full_path, img=image, domain=domain)
        
    def getImages(self, path, name, keep=False, save=False) -> dict:
        """Returns all images of the saved paths from the camera as an dictionary with their IDs as key"""
        images = dict()
        for id in self._files.keys():
            images[id] = self.getImage(id, path, name, keep=True)
            if save:
                images[id].save()
        if not keep:
            self.deleteFiles()
        return images
    
    def download(self, path, name, keep=False):
        """Downloads all images of the saved paths from the camera directly to the file system"""
        for id in self._files.keys():
            self.getImage(id, path, name, keep).unload(save=True)

    def downloadVideo(self, path, name, keep=False):
        """Downloads last video file"""
        for filename in self._files.values():
            ext = os.path.splitext(filename[1])
            if ext.lower() == '.mov' or ext.lower() == '.mp4':
                # Found a video!
                pass

    def listFiles(self, path='/'):
        """Returns list of all files found on the camera"""
        result = []
        # get files
        for name, _ in self.getCam().folder_list_files(path):
            result.append(os.path.join(path, name))
        # read folders
        folders = []
        for name, _ in self.getCam().folder_list_folders(path):
            folders.append(name)
        # recurse over subfolders
        for name in folders:
            result.extend(self.list_files(os.path.join(path, name)))
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


    ### Helper ###
    
    def convertRaw(self, raw_img):
        """Converts raw images to image arrays and returns an image buffer"""
        raw = rawpy.imread(raw_img)
        # Params for post process
        params = rawpy.Params(output_color=rawpy.ColorSpace.raw, noise_thr=20)
        rgb = raw.postprocess(params)
        
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
   
