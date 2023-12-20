

class ImgData:
    def load(self, path):
        frames=[]
        for i in range(2, NUM_IMAGES+1):
            file = os.path.join(os.path.abspath(INPUT_PATH), f"{IMG_NAME}{i:04}.exr")
            frames.append(colour.read_image(file, bit_depth=IMAGE_DTYPE, method='Imageio'))
        original = colour.read_image(os.path.join(os.path.abspath(INPUT_PATH), f"{IMG_NAME}0001.exr"), bit_depth=IMAGE_DTYPE, method='Imageio')
        original = original[:,:,:3] # Only use red channel

    def get(self, index):
        return 0