import taichi as ti
import taichi.math as tm
import taichi.types as tt

# TODO: Class missing
#def FourierSeries(order, u, v):
#    series = np.array([1], dtype=np.float32)
#    for n in range(1, order+1):
#            for m in range(1, order+1):
#                series = np.append(series, (math.cos(n*u)*math.cos(m*v)))
#                series = np.append(series, (math.cos(n*u)*math.sin(m*v)))
#                series = np.append(series, (math.sin(n*u)*math.cos(m*v)))
#                series = np.append(series, (math.sin(n*u)*math.sin(m*v)))
#    return series
#def FourierFactorCount(order):
#    return 4*order*order+1


# TODO: Move to render submodule
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
    
