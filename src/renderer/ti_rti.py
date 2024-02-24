import taichi as ti
import taichi.math as tm
import taichi.types as tt

@ti.kernel
def copyFrame(sequence: ti.template(), frame_index: ti.i32, copy_frame: ti.types.ndarray(dtype=ti.f32, ndim=3)):
    # Iterate over pixels
    H, W = sequence.shape[1], sequence.shape[2]
    for y, x in ti.ndrange(H, W):
        # Copy frame
        sequence[frame_index, y, x] = [copy_frame[y, x, 0], copy_frame[y, x, 1], copy_frame[y, x, 2]]

@ti.kernel
def calculateFactors(sequence: ti.template(), factors: ti.template(), inverse: ti.types.ndarray(dtype=ti.f32, ndim=2), row_offset: ti.i32):
    # Iterate over pixels and factor count
    H, W, C = sequence.shape[1], sequence.shape[2], factors.shape[0]
    for y, x, m in ti.ndrange(H, W, C):
        # Matrix multiplication of inverse and sequence pixels
        for n in range(sequence.shape[0]): # n to 200/sequence count, m to 10/factor count
            factors[m, y+row_offset, x][0] += inverse[m, n] * sequence[n, y, x][0]
            factors[m, y+row_offset, x][1] += inverse[m, n] * sequence[n, y, x][1]
            factors[m, y+row_offset, x][2] += inverse[m, n] * sequence[n, y, x][2]


@ti.kernel
def sampleLight(pix: ti.types.ndarray(dtype=tt.vector(3, ti.f32), ndim=2), A: ti.template(), u: ti.f32, v: ti.f32):
    for y, x in pix:
        pix[y, x] = sampleUV(A, y, x, u, v)
        # Exposure correction (?)
        pix[y, x] *= 10

        
@ti.kernel
def sampleHdri(pix: ti.types.ndarray(dtype=tt.vector(3, ti.f32), ndim=2), A: ti.template(), hdri: ti.template(), rotation: ti.f32):
    samples_y = 10
    samples_x = 40
    rot = 1 - rotation
    for y, x in pix:
        pix[y, x] = 0
        # TODO: Smarter sampling: Should sample on coordinates that are the the brightest for a pixel
        for yy, xx in ti.ndrange(samples_y, samples_x):
            u = yy / (samples_y) * 0.3 + 0.6
            v = xx / samples_x
            pix[y, x] += sampleUV(A, y, x, u, v) / (10) * \
                hdri[ti.cast(u*hdri.shape[0], ti.i32), ti.cast(((v+rot) * hdri.shape[1]) % hdri.shape[1], ti.i32)]
   
@ti.kernel
def sampleNormals(pix: ti.template(), A: ti.template()):
    for y, x in pix:
        # Find coordinates for maximum
        pass

        
@ti.func
def sampleUVFour(A: ti.template(), y: ti.i32, x: ti.i32, u: ti.f32, v: ti.f32):
    rgb = A[0, y, x]
    for m, n in ti.ndrange((1, A.shape[0]), (1, A.shape[0])):
        mult = A[m, y, x] * A[n, y, x]
        rgb += mult * tm.cos(n*u)*tm.cos(m*v) +\
               mult * tm.cos(n*u)*tm.sin(m*v) +\
               mult * tm.sin(n*u)*tm.cos(m*v) +\
               mult * tm.sin(n*u)*tm.sin(m*v)
    return rgb
    

@ti.func
def sampleUV(A: ti.template(), y: ti.i32, x: ti.i32, u: ti.f32, v: ti.f32):
    rgb = A[0, y, x]
    #n = 1, 2, 3, 4, 5, 6, 7, 8, 9
    #a = 1, 1, 2, 2, 2, 3, 3, 3, 3
    #b = 0, 1, 0, 1, 2, 0, 1, 2, 3
    
    rgb += sampleSum(A, y, x, u, v, 1, 1)        
    if A.shape[0] >= 6:
        rgb += sampleSum(A, y, x, u, v, 3, 2)
    if A.shape[0] >= 10:
        rgb += sampleSum(A, y, x, u, v, 6, 3)
    if A.shape[0] >= 15:
        rgb += sampleSum(A, y, x, u, v, 10, 4)
    if A.shape[0] >= 21:
        rgb += sampleSum(A, y, x, u, v, 15, 5)
    if A.shape[0] >= 28: 
        rgb += sampleSum(A, y, x, u, v, 21, 6)
        
    return rgb

@ti.func
def sampleSum(A, y, x, u, v, o, a):
    rgb = A[o, y, x] * u**(a)
    for i in range(1, a+1):
        rgb += A[o+i, y, x] * u**(a-i) * v**i
    return rgb