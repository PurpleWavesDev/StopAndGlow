import logging as log
import numpy as np
from numpy.typing import ArrayLike
import math

import cv2 as cv

from src.imgdata import *

# TODO: Unify, input variable?
DATA_BASE_PATH='../HdM_BA/data/'


class ImgOp:
    ### Color channel stacking ###
    def StackChannels(channels: list[ImgBuffer], path=None) -> ImgBuffer:
        """Stack color channels to a single image"""
        channels_get = [channel.get() for channel in channels]
        return ImgBuffer(path=path, img=np.dstack(channels_get), domain=channels[0].domain())

    ### HDRI Exposure stacking and helpers ###
    def CameraResponse(exposure_stack: list[ImgBuffer]) -> ArrayLike:
        """Calculate the camera response curve from a sequence of images with different exposures"""
        # Estimate camera response
        calibrate = cv.createCalibrateDebevec()
        return calibrate.process([img.get() for img in exposure_stack], [img.getMeta().exposure for img in exposure_stack])

    def ExposureStacking(exposure_stack: list[ImgBuffer], camera_response: ArrayLike = None, path=None) -> ImgBuffer:
        """Generate an HDR image out of a stack of SDR images"""
        # Get Camera response if not provided
        camera_response = ImgOp.CameraResponse(exposure_stack) if camera_response is None else camera_response
        
        # Make HDR image
        merge_debevec = cv.createMergeDebevec()
        hdr = merge_debevec.process([img.get() for img in exposure_stack], [img.meta().exposure for img in exposure_stack], camera_response)
        return ImgBuffer(path, hdr, exposure_stack[0].domain())
    
    ### Numpy Image quick save functions ###
    def SaveBase(img: ArrayLike, name, img_format=ImgFormat.PNG):
        path = os.path.abspath(os.path.join(DATA_BASE_PATH, name))
        buffer = ImgBuffer(img=img, path=path)
        buffer.save(img_format)
        return buffer
    
    def SaveEval(img: ArrayLike, name, img_format=ImgFormat.PNG):
        return ImgOp.SaveBase(img, os.path.join('eval', name), img_format)
    

    ### Image properties ###
    # TODO: numpy arrays or ImgBuffers? Smart int/float logic?
    def similar(img1, img2, threshold=0.1, mask=None) -> bool:
        if mask is not None:
            img = cv.bitwise_and(img, img, mask=mask)
        argmax = np.argmax((img1-img2)>threshold)
        return argmax == 0
    
    def blackframe(img, threshold=50, mask=None) -> bool:
        if mask is not None:
            img = cv.bitwise_and(img, img, mask=mask)
        return np.argmax(img>threshold) == 0
