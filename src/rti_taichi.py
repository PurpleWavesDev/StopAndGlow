import taichi as ti
import taichi.math as tm

ti.init(arch=ti.gpu)

pixels = ti.field(dtype=float, shape=(1920,1080))

def launchViewer(res):
    gui = ti.GUI("RTI Viewer", res=res)
    #pixels = ti.field(dtype=float, shape=res)
    
    u: ti.f32 = 0.5
    v: ti.f32 = 0.5
    while gui.running:
        #v = (v+0.05)%2
        sample(u, v)
        gui.set_image(pixels)
        gui.show()
        #i += 1

@ti.kernel
def sample(u: ti.f32, v: ti.f32):
    for x, y in pixels:
        pixels[x, y] = u
        #pixels[x, y] = self.a(0)[y, x] + self.a(1)[y, x]*u + self.a(2)[y, x]*v + self.a(3)[y, x]*u*v + self.a(4)[y, x]*u**2 + self.a(5)[y, x]*v**2 + self.a(6)[y, x]*u**2 * v + self.a(7)[y, x]*v**2 * u
    
