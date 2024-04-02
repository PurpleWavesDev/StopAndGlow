class RenderSettings:
    def __init__(self, is_linear=False, is_gray=False, as_int=False, with_exposure=False, needs_hdri=False, needs_coords=False, req_keypress_events=False, req_inputs=False):
        self.is_linear=is_linear
        self.is_gray=is_gray
        self.as_int=as_int
        self.with_exposure=with_exposure
        self.needs_hdri=needs_hdri
        self.needs_coords=needs_coords
        self.req_keypress_events=req_keypress_events
        self.req_inputs=req_inputs

class Viewer:
    # Viewer modes and render settings
    def setResolution(self, resolution):
        pass
    def getModes(self) -> list:
        return list()
    def setMode(self, mode):
        pass
    def getRenderSettings(self, mode) -> RenderSettings:
        return RenderSettings()
    def setCoords(self, u, v):
        pass
    def keypressEvent(self, event_key):
        pass
    def inputs(self, window, time_frame):
        pass

    # Rendering
    def render(self, buffer, time_frame):
        pass

