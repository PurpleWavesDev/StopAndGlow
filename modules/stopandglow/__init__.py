# Enable OpenCV EXR support
import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"

# Imports
import sys
import datetime
from typing import Any

DEBUG = hasattr(sys, 'gettrace') and sys.gettrace() is not None


def main(argv):
    # cal stacking
    stack_cals = [Calibration(os.path.join(FLAGS.cal_folder, cal_name)) for cal_name in FLAGS.cal_stack_names]
    hw.cal.stitch(stack_cals)
    hw.cal.save(FLAGS.cal_folder, FLAGS.new_cal_name)

    ### Calibration ###
    if type(renderer) is Calibrate:
        # Save calibration
        cal_name = FLAGS.new_cal_name if FLAGS.new_cal_name != '' else datetime.datetime.now().strftime("%Y%m%d_%H%M") + '_calibration.json' # 240116_2333_calibration.json
        new_cal = renderer.getCalibration()
        log.info(f"Saving calibration as '{cal_name}' with {len(new_cal)} lights from ID {new_cal.getIdBounds()}")
        new_cal.save(FLAGS.cal_folder, cal_name)
        
#################### Light MODES ####################

def lightsAnimate(hw):
    # Function for
    dome = LightCtl(hw)
    def fn_lat(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleWithLatLong(lambda latlong: ImgBuffer.FromPix(50) if latlong[0] > 90-(i*2) else ImgBuffer.FromPix(0))
        dome.writeLights()
        return i<70 # i<45
    def fn_long(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleWithLatLong(lambda latlong: ImgBuffer.FromPix(80 * max(0, 1 - (i*8-latlong[1])/90)) if latlong[1] < i*8 else ImgBuffer.FromPix(0))
        dome.writeLights()
        return i<70 # i<45

    for _ in range(3):
        t = Timer(LightFnWorker(hw, fn_lat, parameter=dome))
        t.start(1/10)
        t.join()

        t = Timer(LightFnWorker(hw, fn_long, parameter=dome))
        t.start(1/10)
        t.join()

def lightsHdriRotate(hw):
    dome = LightCtl(hw)
    hdri = ImgBuffer(os.path.join(FLAGS.hdri_folder, FLAGS.hdri_name), domain=ImgDomain.Lin)
    dome.processHdri(hdri)
    dome.sampleHdri(0)
    img = dome.generateLatLongMapping(hdri)
    imgop.SaveEval(img.get(), "hdri_latlong")
    img = dome.generateUVMapping()
    imgop.SaveEval(img.get(), "hdri_uv")
    
    # Function for
    def fn(lights: Lights, i: int, dome: Any) -> bool:
        dome.sampleHdri(i*3) # 10 degree / second
        dome.writeLights()
        return i<360
    
    t = Timer(LightFnWorker(hw, fn, parameter=dome))
    t.start(1/10)
    t.join()


def lightsRun(hw, ids=None):
    if ids is None:
        ids = hw.cal.getIds()
    log.info(f"Running through {len(ids)} lights with IDs {ids[0]}-{ids[-1]}")
    t = Timer(LightWorker(hw, hw.cal.getIds()))
    t.start(2/25) # 1/20 is max with occational overruns
    t.join()


#################### RELIGHT MODES ####################

def relightSimple(img_seq, calibration, output_name):
    # Deine Funktion, Iris :)
    log.info(f"Generate HDRI Lighting from Sequence")

    dome = LightCtl(calibration)
    hdri = ImgBuffer(os.path.join(FLAGS.seq_folder, FLAGS.input_hdri), domain=ImgDomain.Lin)
    dome.processHdri(hdri)

    # Sequence generator
    for i in range(72):
        lighting = dome.generateLightingFromSequence(img_seq, longitude_offset=i*5)
        lighting.setPath(os.path.join(FLAGS.seq_folder, output_name, f"{output_name}_{i:03d}"))
        lighting.set(lighting.get()*40)
        lighting = lighting.asDomain(ImgDomain.sRGB)
        lighting.setFormat(ImgFormat.JPG)
        lighting.save()
        
    return
    # Generate scene with HDRI lighting 
    lighting = dome.generateLightingFromSequence(img_seq, longitude_offset=FLAGS.hdri_rotation)

    lighting.setPath(os.path.join(FLAGS.seq_folder, output_name, output_name))
    lighting.setFormat(ImgFormat.EXR)
    lighting.save()
