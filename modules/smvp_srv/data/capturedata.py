class CaptureData:
    def __init__(self):
        self.lights: Sequence
        self.preview: ImgBuffer
        self.depth: ImgBuffer
        self.data: {}
    