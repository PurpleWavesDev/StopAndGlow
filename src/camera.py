# Camera imports
import gphoto2 as gp
import rawpy
from PIL import Image
import imageio
imageio.plugins.freeimage.download()

# Process imports
import subprocess
import signal

import os

class Cam:
    def __init__(self):
        # Lets kill any gphoto process that blocks the ressource
        killgphoto2()

        self.cam = gp.Camera()
        self.cam.init()
        self.files = dict()

    def __del__(self):
        self.cam.exit()

    def setRaw(raw=True):
        if raw:
            pass
        else:
            pass

    def capture(self, id):
        # Capture image and safe file path for ID
        file = self.cam.capture(gp.GP_CAPTURE_IMAGE)
        self.files[id] = [file.folder, file.name]

    #def capturePreview 
         # Capture image/preview
        #capture = camera.capture_preview()
        #filedata = capture.get_data_and_size()
        #data = memoryview(filedata)
        #image = Image.open(io.BytesIO(filedata))
        #image.save(f"test_{i}.png")

    #def trigger(self, id):
        #camera.trigger_capture()

    def download(self, path, name='img', delete=True):
        # Download all files with new path and their ID in the name
        for id, file in self.files.items():
            # Create path if not exists
            full_path = os.path.join(path, name)
            if not os.path.exists(full_path):
                os.makedirs(full_path)

            image = self.cam.file_get(file[0], file[1], gp.GP_FILE_TYPE_NORMAL)
            image.save(os.path.join(full_path, f"{name}_{id:03d}{os.path.splitext(file[1])[1]}"))
            if delete:
                self.cam.file_delete(file[0], file[1])

        # Reset dict
        self.files = dict()

    def list_files(self, path='/'):
        result = []
        # get files
        for name, _ in self.cam.folder_list_files(path):
            result.append(os.path.join(path, name))
        # read folders
        folders = []
        for name, _ in self.cam.folder_list_folders(path):
            folders.append(name)
        # recurse over subfolders
        for name in folders:
            result.extend(self.list_files(os.path.join(path, name)))
        return result

    def add_files(self, file_list, start_number=1):
        for name in file_list:
            self.files[start_number] = os.path.split(name)
            start_number+=1

    def toPng(self): #TODO!
        # Convert and save image (reads file again)
        raw = rawpy.imread(target)
        params=rawpy.Params(output_color=rawpy.ColorSpace.sRGB, noise_thr=20)
        rgb = raw.postprocess(params)
        imageio.imsave('default.png', rgb)




#kill gphoto2 process that occurs whenever connect camera
def killgphoto2():
    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out,err = p.communicate()
    for line in out.splitlines():
        if b'gvfsd-gphoto2' in line:
            #kill process
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)
   
