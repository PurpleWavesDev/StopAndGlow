import logging as log
import numpy as np
import math

import cv2 as cv

# TODO: numpy arrays or ImgBuffers? Smart int/float logic?
class ImgOp:
    def similar(img1, img2, threshold=0.1, mask=None) -> bool:
        if mask is not None:
            img = cv.bitwise_and(img, img, mask=mask)
        return not np.argmax((img1-img2)>=threshold)
    
    def blackframe(img, threshold=50, mask=None) -> bool:
        if mask is not None:
            img = cv.bitwise_and(img, img, mask=mask)
        return np.argmax(img>threshold) == 0

