import os
import logging as log

import colour
import imageio
imageio.plugins.freeimage.download()


IMAGE_DTYPE='float16'

class ImgBuffer:
    def __init__(self, path):
        self.path=path
        self.img=None
        
    def get(self):
        if self.img is None:
            self.load()
        return self.img

    def set(self, img):
        self.img=img

    def load(self):
        self.img = colour.read_image(self.path, bit_depth=IMAGE_DTYPE, method='Imageio')
        #original = original[:,:,:3] # Only use red channel

class ImgData:
    def __init__(self, path):
        self.start=-1
        self.stop=-1
        self.load_folder(os.path.abspath(path))

    def load_folder(self, path):
        # Search for frames in folder
        self.frames = [ImgBuffer(os.path.join(path, f)) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        log.debug(f"Loaded {len(self.frames)} images from path {path}")

    def get(self, index, delete=False):
        img = self.frames[index].get()
        if delete:
            self.frames[index].set(None)
        return img

    def __len__(self):
        return self.stop-self.start