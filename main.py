
print("Running!")

import math
import copy
from PIL import Image


img = Image.new("RGBA", (640, 640))
px = img.load()


for x in range(0, img.width):
    for y in range(0, img.height):
        px[x, y] = (0, 0, 0, 255)

class Vec:

    def __init__(self, x = 0, y = 0, z = 0, w = 1):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

    def __add__(self, other):
        return Vec(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vec(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vec(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar):
        return Vec(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self):
        return self * -1

    def length(self):
        return math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z)

    def normalized(self):
        return self / self.length()

    def dot(self, b):
        a = self
        return a.x*b.x + a.y*b.y + a.z*b.z

    def cross(self, b):
        a = self
        return Vec(a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y*b.x)

    def __str__(self):
        return "<%.2f, %.2f, %.2f, %.2f>" % (self.x, self.y, self.z, self.w)

    def __eq__(self, other):
        return isinstance(other, Vec) and self.x == other.x and self.y == other.y and self.z == other.z and self.w == other.w

# Implemented as row-major
class Mat:

    def __getitem__(self, item):
        if isinstance(item, tuple):
            if len(item) != 2:
                raise KeyError("Expecting 2 element tuple for 2D matrices.")
            r = item[0]
            c = item[1]
            if not isinstance(r, int) or not isinstance(c, int):
                raise KeyError("Row and Column indices should be integers.")
            if r < 1 or r > self.rows:
                raise KeyError("Row %d is out of bounds [1, %d]" % (r, self.rows))
            if c < 1 or c > self.cols:
                raise KeyError("Column %d is out of bounds [1, %d]" % (c, self.cols))
            r -= 1
            c -= 1
            return self.elements[r*self.cols + c]
        else:
            raise KeyError("Index should be a tuple.")


    def __init__(self, elements = None):
        self.rows = 4
        self.cols = 4

        self.elements = elements or [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def __mul__(self, v):
        if isinstance(v, Vec):
            p = copy.copy(v)
            e = self.elements
            p.x = v.x*e[ 0] + v.y*e[ 1] + v.z*e[ 2] + v.w*e[ 3]
            p.y = v.x*e[ 4] + v.y*e[ 5] + v.z*e[ 6] + v.w*e[ 7]
            p.z = v.x*e[ 8] + v.y*e[ 9] + v.z*e[10] + v.w*e[11]
            p.w = v.x*e[12] + v.y*e[13] + v.z*e[14] + v.w*e[15]

            return p
        else:
            e1 = self.elements
            e2 = v.elements

            p = Mat()
            ep = p.elements

            for r in range(0, 4):
                for c in range(0, 4):
                    val = 0
                    for i in range(0, 4):
                        val += e1[r*4 + i] * e2[i*4 + c]
                    ep[r*4 + c] = val

            return p


    def __eq__(self, other):
        return isinstance(other, Mat) and self.elements == other.elements


    def __str__(self):
        rows = self.rows
        cols = self.cols
        elements = self.elements
        s = ""
        for i in range(0, rows * cols):
            if i > 0:
                s += ", "
                if i % cols == 0:
                    s += "\n"
            s += str(elements[i])

        return s

m = Mat([
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
])
assert(m[1, 1] == 1)

assert(m * m == m)

v = Vec(1, 2, 3)
assert(m * v == v)

m = Mat([
     1,  2,  3,  4,
     5,  6,  7,  8,
     9, 10, 11, 12,
    13, 14, 15, 16,
])
assert(Mat() * m == m)

def makeProjection(width, height, near = 1, far = 1000):
    r = 1.0 # right (left = -right)
    t = 1.0 # top (bottom = -top)
    n = near # near
    f = far # far
    d = f-n # depth = far - near

    return Mat([
        n/r, 0, 0, 0,
        0, n/t, 0, 0,
        0, 0, (f+n)/d, (-2*f*n)/d,
        0, 0, 1, 0,
    ])


def getPlane(a, b, c):
    norm = (a-c).cross(a-b).normalized()
    d = -(norm.x*a.x + norm.y*a.y + norm.z*a.z)
    norm.w = d
    return norm

class Rasterizer:

    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

        # bouding rectangle
        self.bmin = Vec(min(a.x, b.x, c.x)-1, min(a.y, b.y, c.y)-1, min(a.z, b.z, c.z)-1)
        self.bmax = Vec(max(a.x, b.x, c.x)+1, max(a.y, b.y, c.y)+1, max(a.z, b.z, c.z)+1)

        self.plane = getPlane(a, b, c)

        print(self.plane)

        self.cur = Vec(self.bmin.x - 1, self.bmin.y, 0)

        self.popFront();

    def sign(self, a, b, c):
        return (a.x - c.x) * (b.y - c.y) - (b.x - c.x) * (a.y - c.y)
    def pointInside(self, p):
        threshold = 0.1
        b1 = self.sign(p, self.a, self.b) <= threshold
        b2 = self.sign(p, self.b, self.c) <= threshold
        b3 = self.sign(p, self.c, self.a) <= threshold
        return (b1 == b2) and (b2 == b3)

    def next(self):
        cur = self.cur
        cur.x += 1
        if cur.x > self.bmax.x:
            cur.x = self.bmin.x
            cur.y += 1

        plane = self.plane
        cur.z = -(plane.x*(cur.x+0.5) + plane.x*(cur.y+0.5) + plane.w)

        self.cur = cur
        self.curi = Vec(int(cur.x), int(cur.y), cur.z)

    def empty(self):
        return self.cur.x > self.bmax.x or self.cur.y > self.bmax.y

    def front(self):
        return (self.curi, self.cur)

    def popFront(self):
        while not self.empty():
            self.next()
            if self.pointInside(self.curi + Vec(0.5, 0.5, 0)):
                break


# rast = Rasterizer((10, 50), (100, 50), (50, 80))
#
# while not rast.empty():
#     p = rast.front()
#     px[p[0], p[1]] = (255, 255, 255, 255)
#     rast.popFront()

def roty(a):
    return Mat([
        math.cos(a) , 0, math.sin(a), 0,
        0           , 1, 0          , 0,
        -math.sin(a), 0, math.cos(a), 0,
        0           , 0, 0          , 1,
    ])

def rotx(a):
    return Mat([
        1, 0          , 0           , 0,
        0, math.cos(a), -math.sin(a), 0,
        0, math.sin(a), math.cos(a) , 0,
        0, 0          , 0           , 1,
    ])

def translate(v):
    return Mat([
        1, 0, 0, v.x,
        0, 1, 0, v.y,
        0, 0, 1, v.z,
        0, 0, 0, 1,
    ])

def lookat(eyefocus, eyepos, eyeu = Vec(0, 1, 0)):
    # camera forward
    f = (eyefocus-eyepos).normalized()
    # camera right
    r = f.cross(eyeu)
    # camera up
    u = r.cross(f)
    return Mat([
        r.x, r.y, r.z, 0,
        u.x, u.y, u.z, 0,
        -f.x, -f.y, -f.z, 0,
        0  , 0  , 0  , 1,
    ]) * Mat([
        1, 0, 0, -eyepos.x,
        0, 1, 0, -eyepos.y,
        0, 0, 1, -eyepos.z,
        0, 0, 0, 1,
    ])

proj = makeProjection(img.width, img.height)
transformation = proj*lookat(Vec(8, 0, 8), Vec(10, -2, -20)*0.6)

lightdir = Vec(0.3, -1, 0.5).normalized()

depth = [-2] * (img.width * img.height)

def setDepth(p, d):
    depth[p.x + p.y*img.width] = d

def getDepth(p):
    if p.x + p.y*img.width >= len(depth):
        print(p)
    return depth[p.x + p.y*img.width]

def pdiv(p):
    w = p.w
    return Vec(p.x/w, p.y/w, p.z/w)

def toscreen(p):
    w = img.width/2
    h = img.height/2
    return Vec(p.x*w + w, -p.y*h + h, p.z)

def drawTriangle(a, b, c):

    # triangle normal
    norm = (a-c).cross(a-b).normalized()
    # facing towards light [0, 1]
    ftl = math.acos(norm.dot(lightdir)) / math.pi

    a = pdiv(transformation*a)
    b = pdiv(transformation*b)
    c = pdiv(transformation*c)

    sa = toscreen(a)
    sb = toscreen(b)
    sc = toscreen(c)

    print(sa, sb, sc)

    for s in (sa, sb, sc):
        if s.x < 0 or s.y < 0 or s.x >= img.width or s.y >= img.height:
            return

    rast = Rasterizer(sa, sb, sc)

    # ambience
    a = 50
    # maximum
    m = 200
    # light
    l = a + (m-a)*ftl


    while not rast.empty():
        pix, p = rast.front()
        if pix.x < 0 or pix.y < 0 or pix.x >= img.width or pix.y >= img.height:
            break
        d = getDepth(pix)
        if p.z >= -1 and (d < -1 or p.z < getDepth(pix)):
            px[pix.x, pix.y] = (int(l), int(l), int(l), 255)
            setDepth(pix, p.z)
        rast.popFront()

def drawRectangle(a, b, c, d):
    drawTriangle(a, b, c)
    drawTriangle(a, c, d)


def drawCube(w, h, d):
    lll = Vec(-w, -h, -d)
    llh = Vec(-w, -h,  d)
    lhl = Vec(-w,  h, -d)
    lhh = Vec(-w,  h,  d)

    hll = Vec( w, -h, -d)
    hlh = Vec( w, -h,  d)
    hhl = Vec( w,  h, -d)
    hhh = Vec( w,  h,  d)

    # left
    drawRectangle(lll, llh, lhh, lhl)
    # right
    drawRectangle(hll, hhl, hhh, hlh)
    # bottom
    drawRectangle(lll, hll, hlh, llh)
    # top
    drawRectangle(lhl, lhh, hhh, hhl)
    # back
    drawRectangle(llh, hlh, hhh, lhh)

f = open("graph.csv", "r")
data = []
minval = None
maxval = None
for line in f:
    row = []
    for s in line.split(","):
        val = float(s.strip())
        row.append(val)
        if minval == None or val < minval:
            minval = val
        if maxval == None or val > minval:
            maxval = val
    data.append(row)

for row in data:
    for i in range(0, len(row)):
        row[i] = (row[i] - minval) / maxval

for ri in range(0, len(data)-1):
    row1 = data[ri+0]
    row2 = data[ri+1]
    l = min(len(row1), len(row2))
    for ci in range(0, l-1):
        elevation = 5
        a = Vec(ri+0, row1[ci+0]*elevation, ci+0)
        b = Vec(ri+1, row2[ci+0]*elevation, ci+0)
        c = Vec(ri+0, row1[ci+1]*elevation, ci+1)
        d = Vec(ri+1, row2[ci+1]*elevation, ci+1)
        drawRectangle(a, b, d, c)

img.save("graph.png")
