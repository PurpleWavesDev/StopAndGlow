import logging as log
import numpy as np
from numpy.typing import ArrayLike
import math

import cv2 as cv

from ..data.imgbuffer import *

# TODO: Unify, input variable?
DATA_BASE_PATH='../HdM_BA/data/'


### Color channel stacking ###
def StackChannels(channels: list[ImgBuffer], path=None) -> ImgBuffer:
    """Stack color channels to a single image"""
    channels_get = [channel.get() for channel in channels]
    return ImgBuffer(path=path, img=np.dstack(channels_get), domain=channels[0].domain())

### Numpy Image quick save functions ###
def SaveBase(img: ArrayLike, name, img_format=ImgFormat.PNG):
    path = os.path.abspath(os.path.join(DATA_BASE_PATH, name))
    buffer = ImgBuffer(img=img, path=path)
    buffer.save(img_format)
    return buffer
    
def SaveEval(img: ArrayLike, name, img_format=ImgFormat.PNG):
    return SaveBase(img, os.path.join('eval', name), img_format)
    

### Image properties ###
# TODO: numpy arrays or ImgBuffers? Smart int/float logic?
def similar(img1, img2, threshold=50, mask=None) -> bool:
    if mask is not None:
        img1 = cv.bitwise_and(img1, img1, mask=mask)
        img2 = cv.bitwise_and(img2, img2, mask=mask)
    return np.max(img1-img2) < threshold
    
def blackframe(img, threshold=50, mask=None) -> bool:
    if mask is not None:
        img = cv.bitwise_and(img, img, mask=mask)
    return np.max(img) < threshold
