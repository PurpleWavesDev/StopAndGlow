import modules.smvp_srv as smvp

from absl import app
from absl import flags

FLAGS = flags.FLAGS

### Example of usage for domectl
# domectl --capture --hdr --seq-type=lights|hdri|fullrun --seq-name="" --seq-domain=keep|linear|srgb --seq-save --seq-convert
# domectl --process --eval-type=cal|hdri|lightstack|rti|expostack|convert --eval-folder="" --eval-name=""
# domectl --viewer --headless --record --record-folder="" --record-name="" --hdri-folder="" --hdri-name=""
# domectl --camctl=none|stop|erase
# domectl --lightctl=none|on|off|run|anim-latlong|hdri --brightness=0-255 --limiter=0-255
# Command chaining (can't be done with abseil)
# domectl capture --hdr --type=lights convert --scale=hd process --type=rti --option=setting:value save --type=processed --viewer

### Global flag defines ###
# General
flags.DEFINE_enum('loglevel', 'INFO', ['ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE'], 'Level of logging.')
# Capture Settings
flags.DEFINE_bool('capture', False, "Set this flag to capture footage instead of loading it from disk.")
flags.DEFINE_bool('hdr', False, "If set, capture will be either raw images or multiple videos for exposure stacking, depending on the camera mode.")
flags.DEFINE_integer('hdr_bracket_num', 3, 'Number of videos to capture for exposure blending in HDR mode.')
flags.DEFINE_integer('hdr_bracket_stops', 4, 'Stops increase for each capture for HDR blending.')
flags.DEFINE_float('capture_fps', 25, 'Frame rate for the video capture.')
flags.DEFINE_integer('capture_frames_skip', 3, 'Frames to skip between frames in video sequence, has to be odd or will be incremented to next odd value.', lower_bound=0)
flags.DEFINE_integer('capture_dmx_repeat', 0, "How many signals should be sent before an image is captured or extracted from video.")
flags.DEFINE_integer('capture_max_addr', 310, "Max address to be used for generating calibrations.")
# Sequence settings
flags.DEFINE_enum('seq_type', 'lights', ["lights", "hdri", "fullrun"], "Sequence consists of images from all lights of the current config, three images for RGB channel stacking or a full run for all light IDs without config.")
flags.DEFINE_enum('seq_domain', 'keep', ['keep', 'lin', 'srgb'], 'Domain of sequence, default for EXR is linear, sRGB for PNGs and JPGs.')
flags.DEFINE_string('seq_folder', '../HdM_BA/data/capture', 'Where the image data should be written to.')
flags.DEFINE_string('seq_name', '', 'Name of captured sequence or folder/file to load, default is current date & time + type of capture.')
flags.DEFINE_bool('seq_save', True, "Save downloaded images to disk.")
flags.DEFINE_bool('seq_convert', False, "Convert to image files if a video was captured.")
# Calibration
flags.DEFINE_string('cal_folder', '../HdM_BA/data/config', 'Folder for light calibration.')
flags.DEFINE_string('cal_name', 'lightdome.json', 'Name of calibration file to be loaded or generated.')
flags.DEFINE_list('cal_stack_names', [], 'List of calibration file names to be stacked to the main calibration file.')
flags.DEFINE_string('new_cal_name', 'lightdome_new.json', 'Name of calibration file to be loaded or generated.')
# HDRI
flags.DEFINE_string('hdri_folder', '../HdM_BA/data/hdri', 'Folder for HDRI environment maps.')
flags.DEFINE_string('hdri_name', '', 'Name of HDRI image to be used for processing.')
flags.DEFINE_float('hdri_rotation', 0.0, 'Rotation of HDRI in degrees.', lower_bound=0, upper_bound=360)
# Processing
flags.DEFINE_bool('process', False, "Set this flag to enable processing of recorded footage.")
flags.DEFINE_enum('eval_type', 'pass', ["cal", "calstack", "rgbstack", "lightstack", "rti", "expostack", "convert", 'pass'], "How the sequence should be processed or interpreted by the viewer.")
flags.DEFINE_bool('eval_dontsave', False, "Set this flag to discard evaluation data after processing.")
flags.DEFINE_string('eval_folder', '../HdM_BA/data/processed', 'Folder for HDRI environment maps.')
flags.DEFINE_string('eval_name', '', 'Name of HDRI image to be used for processing.')
flags.DEFINE_enum('convert_to', 'exr_hd', ['jpg', 'exr', 'jpg_hd', 'exr_hd', 'jpg_4k', 'exr_4k', 'scale_hd', 'scale_4k'], "Convert images / video to JPGs as sRGB or EXRs as linear domain, keeping resoultion or scaling to HD or 4K.")
# Viewer
flags.DEFINE_bool('viewer', False, "Set this flag to launch the viewer with the loaded or processed data.")
flags.DEFINE_bool('live', False, "Starting the viewer in live mode.")
flags.DEFINE_bool('record', False, "Set this flag to record a 360° environment turn in headless mode.")
flags.DEFINE_string('rec_folder', '../HdM_BA/data/rec', 'Folder for recorded renderings.')
flags.DEFINE_string('rec_name', '', 'Name of video output of recorded rendering.')
# Camera control
flags.DEFINE_enum('camctl', 'none', ["none", "stop", "erase"], "")
# Light control
flags.DEFINE_enum('lightctl', 'none', ["none", "on", "top", "off", "run", "anim_latlong", "anim_hdri"], "How the sequence should be processed or interpreted by the viewer.")


if __name__ == '__main__':
    smvp.FLAGS = FLAGS
    app.run(smvp.main)
