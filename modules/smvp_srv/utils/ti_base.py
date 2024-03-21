import taichi as ti
import taichi.math as tm
import taichi.types as tt

# Types
pixvec = tt.vector(3, ti.f32)
pixvec8 = tt.vector(3, ti.u8)
pixarr = tt.ndarray(pixvec, 2)
pixarr8 = tt.ndarray(pixvec8, 2)
pixarr_tpl = tt.ndarray(ndim=2)

XYZtosRGB =  ti.Matrix([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]], dt=ti.f32)
sRGBtosXYZ = ti.Matrix([[0.4124,  0.3576,  0.1805], [ 0.2126, 0.7152, 0.0722], [0.0193,  0.1192, 0.9505]], dt=ti.f32)

class TIBase:
    gpu = True
    debug = True
    _initialized = False
    
    def init():
        if not TIBase._initialized:
            ti.init(arch=ti.gpu if TIBase.gpu else ti.cpu, debug=TIBase.debug)
            TIBase._initialized = True

@ti.kernel
def lin2sRGB(pix: tt.ndarray(tt.vector(3, ti.f32), ndim=2), exposure: ti.f32):
    for y, x in pix:
        # Chroma correction from D65
        #pix[y, x] = XYZtosRGB @ pix[y, x]
        
        # Gamma correction
        pix[y, x] = pix[y, x] * exposure
        for i in range(3):
            if pix[y, x][i] > 0.0031308:
                pix[y, x][i] = 1.0055 * (pix[y, x][i]**(1/2.4)) - 0.055
            else:
                pix[y, x][i] = 12.92 * pix[y, x][i]

@ti.kernel
def sRGB2Lin(pix: tt.ndarray(tt.vector(3, ti.f32), ndim=2)):
    for y, x in pix:
        # Gamma correction
        for i in range(3):
            if pix[y, x][i] > 0.04045:
                pix[y, x][i] = ((pix[y, x][i]+0.055) / 1.055)**2.4
            else:
                pix[y, x][i] = pix[y, x][i] / 12.92
                
        # Chroma correction, D65 (?)
        #pix[y, x] = sRGBtosXYZ @ pix[y, x]

@ti.kernel
def exposure(pix: tt.ndarray(tt.vector(3, ti.f32), ndim=2), exposure: ti.f32):
    for y, x in pix:
        pix[y, x] = pix[y, x] * exposure
    
@ti.kernel
def transpose(field_in: ti.template(), field_out: ti.template()):
    for x, y in field_out:
        field_out[x, field_out.shape[1]-y-1] = field_in[y, x]
   

@ti.kernel
def copyFrameToSequence(sequence: ti.template(), frame_index: ti.i32, copy_frame: pixarr):
    # Iterate over pixels
    H, W = sequence.shape[1], sequence.shape[2]
    for y, x in ti.ndrange(H, W):
        # Copy frame
        sequence[frame_index, y, x] = copy_frame[y, x]
