import numpy as np
import dask.array as da
"""
The plan for all of this is to simply compute everything as numpy arrays from dask arrays (and accept the memory hit)
If an when this has to be better I will loop through the dask arrays, block by block, to see if that works
(Theorectically it should I am just to busy/lazy to do it right now)
"""


"""
Stuff I stole from pySW4
"""

"""
Write rfile header.

Parameters
----------
f : file
    Open file handle in ``'wb'`` mode

magic : int
    Determine byte ordering in file. Defaults to 1.

precision : int
    The number of bytes per entry in the data section.

    4 - single precision (default)

    8 - double precision

attenuation : int
    Indicates whether the visco-elastic attenuation parameters QP
    and QS are included in the data section.
    0 - no visco-elastic attenuation parameters included
    1 - visco-elastic attenuation parameters included (default)

az : float
    Angle in degrees between North and the positive x-axis.
    Defaults to 0. See the
    `SW4 User Guide <https://geodynamics.org/cig/software/sw4/>`_.

lon0, lat0 : float
    Longitude and Latitude of the origin of the data.
    Defaults to 33.5, 28.0 .

proj_str : str
    Projection string which is read by the Proj4 library if SW4 was
    built with Proj4 support. See the
    `SW4 User Guide <https://geodynamics.org/cig/software/sw4/>`_
    and the `Proj4 <https://trac.osgeo.org/proj/wiki/GenParms>`_
    documentation. Defaults to
    '+proj=utm +zone=36 +datum=WGS84 +units=m +no_defs'.

nb : int
    The number of blocks in the data section. Must be > 0.
    Defaults to 1.
"""
def write_hdr(f, magic=1, precision=4, attenuation=1,
              az=0.0, lon0=33.5, lat0=28.0,
              proj_str="+proj=utm +zone=36 +datum=WGS84 +units=m +no_defs", nb=1):
    
    magic        = np.int32(magic)
    precision    = np.int32(precision)
    attenuation  = np.int32(attenuation)
    az           = np.float64(az)
    lon0         = np.float64(lon0)
    lat0         = np.float64(lat0)
    mlen         = np.int32(len(proj_str))
    nb           = np.int32(nb)
    #encode the projection string
    proj_str = proj_str.encode('ascii')
    hdr = [magic, precision, attenuation, az, lon0, lat0, mlen, proj_str, nb]
    for val in hdr:
        f.write(val)
    return
 
"""
Write rfile block header

Block headers are appended after the rfile header has been written.
All block headers are written one after the other.

Parameters
----------
f : file
    Open file handle in ``'wa'`` mode.

hh, hv : numpy.float64
    Grid size in the horizontal (x and y) and vertical (z)
    directions  in meters.

z0 : numpy.float64
    The base z-level of the block. Not used for the
    first block which holds the elevation of the topography/
    bathymetry.

nc : int
    The number of components:

    The first block holds the elevation of the topography/
    bathymetry, so ``nc=1``.
    The following blocks must have either 3 if only rho, vp, and vs
    are present (``attenuation=0``) or 5 if qp and qs are pressent
    (``attenuation=1``).

ni, nj, nk : int
    Number of grid points in the i, j, k directions.

    Because the topography/bathymetry is (only) a function of the
    horizontal coordinates, the first block must have ``nk=1``.
""" 

def write_block_hdr(f, hh, hv, z0, nc, ni, nj, nk):
    f.write(np.float64(hh))
    f.write(np.float64(hv))
    f.write(np.float64(z0))
    f.write(np.int32(nc))
    f.write(np.int32(ni))
    f.write(np.int32(nj))
    f.write(np.int32(nk))





"""
Parameters
----------
f : file or str
    Open file handle in ``'wa'`` mode or path to an rfile for
    appending data to the end.

data : :class:`~numpy.ndarray`
    Elevation data in meters below sea level (z positive down).

precision : {4 (default), 8}
    The number of bytes per entry in the data section.

    4 - single precision

    8 - double precision
"""

def write_topo_block(f, data, precision=4):
    data = data
    try:
        with open(f, 'wa') as f:
            data.astype(np.float32).tofile(f)
    except TypeError:
        data.astype(np.float32).tofile(f)

"""
Write material properties at a point `i`, `j` in block `b`.

This is a convenient function to use while looping over `i`, `j` in
a specific block `b` for writing out material properties at each
index `k`. At the very least `vp` should be provided. If only `vp`
is provided, the other properties are calculated using the
:mod:`~..material_model` module.

Parameters
----------
f : file
    Open file handle in ``'wa'`` mode for appending data to the end
    of a file in construction ot in ``'r+b'`` mode for overwriting
    existing data.

    When overwriting existing data, the user must take care to place
    the cursor in the right place in the file.

vp : array-like
    P wave velocity at indices of `k` in m/s.

nc : int
    Number of components to write out. Either 3 (`rho`, `vp`, and
    `vs` if ``attenuation=0``) or 5 (also `qp` and `qs` if
    ``attenuation=1``).

vs : array-like, optional
    S wave velocity at indices of `k` in m/s. If not given, `vs` is
    calculated from :func:`~..material_model.get_vs`.

rho : array-like, optional
    Density at indices of `k` in kg/m^3. If not given, `rho` is
    calculated from :func:`~..material_model.get_rho`.

qp : array-like, optional
    P quality factor at indices of `k`. If not given, `qp` is
    calculated from :func:`~..material_model.get_qp`.

qs : array-like, optional
    S quality factor at indices of `k`. If not given, `qs` is
    calculated from :func:`~..material_model.get_qs`.

shape : shape of the coordinate grid (so that I can orient the output data correctly)
"""

def write_properties(f, vp, nc, vs, rho, qp, qs,shape):
    vp = vp
    k_array = np.empty((vp.size, nc), np.float32)
    vs = vs 

    rho = rho     
    qs = qs
    qp = qp
    k_array[:, 0] = rho
    k_array[:, 1] = vp
    k_array[:, 2] = vs
    try:
        k_array[:, 3] = qp
        k_array[:, 4] = qs
    except IndexError:
        pass

    k_array.tofile(f)

