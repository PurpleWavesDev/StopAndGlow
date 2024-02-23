import taichi as ti
import taichi.math as tm

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
def sampleLight(pix: ti.template(), A: ti.template(), u: ti.f32, v: ti.f32):
    for y, x in pix:
        pix[y, x] = sampleUVFour(A, y, x, u, v)
        # Exposure correction (?)
        pix[y, x] *= 10

        
@ti.kernel
def sampleHdri(pix: ti.template(), A: ti.template(), hdri: ti.template(), rotation: ti.f32):
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
    # (1, 3,) 6, 10, 15, 21
    # Grade 3
    rgb = A[0, y, x] + A[1, y, x] * u + A[2, y, x] * v +\
        A[3, y, x] * u*v + A[4, y, x] * u**2 + A[5, y, x] * v**2
    if A.shape[0] >= 10:
        # Grade 4
        rgb += A[6, y, x] * u**2 * v + A[7, y, x] * v**2 * u +\
            A[8, y, x] * u**3 + A[9, y, x] * v**3
    if A.shape[0] >= 15:
        # Grade 5
        rgb += A[10, y, x] * u**2 * v**2 + A[11, y, x] * u**3 * v + A[12, y, x] * u * v**3 +\
            A[13, y, x] * u**4 + A[14, y, x] * v**4
    if A.shape[0] >= 21:
        # Grade 6
        rgb += A[15, y, x] * u**3 * v**2 + A[16, y, x] * u**2 * v**3 +\
            A[17, y, x] * u**4 * v + A[18, y, x] * u * v**4 +\
            A[19, y, x] * u**5 + A[20, y, x] * v**5
    return rgb

