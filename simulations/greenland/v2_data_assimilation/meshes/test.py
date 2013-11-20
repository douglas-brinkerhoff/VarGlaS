import sys
import os
src_directory = '../../../../'
sys.path.append(src_directory)

import src.physical_constants as pc
from data.data_factory   import DataFactory
from pylab               import *
from gmshpy              import *
from scipy.interpolate   import RectBivariateSpline
from src.utilities       import DataInput

#===============================================================================
# data preparation :

thklim = 200.0

# collect the raw data :
bamber   = DataFactory.get_bamber(thklim = thklim)
searise  = DataFactory.get_searise(thklim = thklim)
meas_shf = DataFactory.get_shift_gre_measures()

dbv     = DataInput("../results/", ("Ubmag_measures.mat", "Ubmag.mat"), 
                    gen_space=False)
dbv.set_data_min('Ubmag', 0.0,   0.0)
dbv.set_data_max('Ubmag', 500.0, 500.0)
dsr  = DataInput(None, searise,  gen_space=False)
dbm  = DataInput(None, bamber,   gen_space=False)
dmss = DataInput(None, meas_shf, gen_space=False, flip=True)
dsr.change_projection(dbm)

# might want to refine off of thickness :
H   = dbm.data['H_n'].copy().T

# ensure that there are no values less than 1 for taking log :
#vel = dsr.data['U_ob'].copy().T
vel  = dbv.data['Ubmag'].copy().T
vel += 1

# invert the sections where the velocity is low to refine at divide :
data                = log(vel)
mv                  = data.max()
k                   = 1
data[2*data < k*mv] = -data[2*data < k*mv]  + k*mv

# plot to check :
imshow(data.T[::-1,::-1])
colorbar()
show()

# x- and y-values for creating nearest-neighbor spline interpolation :
xs     = dbm.x
ys     = dbm.y
spline = RectBivariateSpline(xs, ys, data, kx=1, ky=1)

#===============================================================================
# GMSHing stuff :

#load the mesh into a GModel
m = GModel.current()
m.load("mesh.geo")

#boolean options are stored as floating point numbers in gmsh => 0. is False
GmshSetOption("Mesh", "CharacteristicLengthFromPoints", 0.)
GmshSetOption("Mesh", "CharacteristicLengthExtendFromBoundary", 0.)
GmshSetOption("Mesh", "Smoothing", 100.)

#the callback can be a member function
class attractor:
  """
  Create an attractor object which refines with min and max cell radius <lmin>,
  <lmax> over data field <field>.  The <f_max> parameter specifies a max value
  for which to apply the minimum cell size such that if <field>_i is less than 
  <f_max>, the cell size in this region will be <lmax>.  If <hard_cut> is true,
  the values of <field> above <lmax> will be set to <lmin>, otherwise regular
  interpolation based on <field> is performed.  If <inv> = True the object 
  refines on the inverse of the data field <field>.
  """
  def __init__(self, field, f_max, lmin, lmax, hard_cut=False, inv=True):
    self.field    = field
    self.lmin     = lmin
    self.lmax     = lmax
    self.f_max    = f_max
    self.hard_cut = hard_cut
    self.inv      = inv
    self.c        = (self.lmax - self.lmin) / self.field.max()
  
  def op(self, x, y, z, entity):
    v = spline(x,y)[0][0]
    if v > self.f_max:
      if self.hard_cut:
        return self.lmin
      else:
        if self.inv:
          lc = self.lmax - self.c * v
        else:
          lc = self.lmin + self.c * v
        return lc
    else:
      return self.lmax

class min_field:
  """
  Return the minimum of a list of attactor operator fields <f_list>.
  """
  def __init__(self, f_list):
    self.f_list = f_list

  def op(self, x, y, z, entity):
    l = []
    for f in self.f_list:
      l.append(f(x,y,z,entity))
    return min(l)


#lmax      = 50000
#lmin      = 2000
#lmin_max  = 5000
#lmin_min  = 500
#num_cuts  = 5
#fmax_max  = 8.0
#a_list    = []
#lc_list   = linspace(lmin_max, lmin_min, num_cuts)
#fmax_list = linspace(0, fmax_max, num_cuts)
#for fmax, l_min in zip(fmax_list, lc_list):
#  a = attractor(data, fmax, l_min, lmax, hard_cut=False)
#  a_list.append(a.op)
#  m.getFields().addPythonField(a.op)

#m1  = min_field(a_list)
#mid = m.getFields().addPythonField(m1.op)
#m.getFields().setBackgroundFieldId(mid)

#a1 = attractor(data, 0.0, 1000, 50000/3.5, inv=True)
#a2 = attractor(data, 0.0, 1000, 50000/3.5, inv=False)
#m1 = min_field([a1.op, a2.op])
#aid1 = m.getFields().addPythonField(a1.op)
#aid2 = m.getFields().addPythonField(a2.op)
#mid  = m.getFields().addPythonField(m1.op)

#m.getFields().setBackgroundFieldId(mid)

a   = attractor(data, 0.0, 1000, 50000, inv=True)
aid = m.getFields().addPythonField(a.op)
m.getFields().setBackgroundFieldId(aid)

#m.extrude(0,0,1) #FIXME: not working, need to generate mesh within gmshpy

#launch the GUI
FlGui.instance().run()

#instead of starting the GUI, we could generate the mesh and save it
#m.mesh(2) # 2 is the dimension
#m.save("square.msh")


