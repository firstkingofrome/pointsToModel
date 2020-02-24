"""
Routines for building the HDF5 based grid file from grid_control configuration file, for injecting low volumes of points
into the hdf5 grid file, for injecting topography into the grid file and for injecting units based off of material properties

.. module:: grid

:author:
    Eric E. Eckert

:copyright:
    Eric E. Eckert eeckert A t nevada d_0_t uNr d-o-T edu

:license:
    BSD 2-Clause License
    
"""
import numpy as np
from scipy.interpolate import griddata #for use on the DEM only!, transition to sklearn or some other dask friendly alternative once memory requires
import json
import h5py
#dask stuff
import dask.array as da
import dask.bag as db
from dask import delayed
import itertools
import logging #todo actually use this once the complexity dictates it, maybe just throw exceptions?

#array operations that cannot go into classes
#there is a bug in dask which causes classed array opperations to be run as delayed operations which prevents
#me from saving the results of large operations directly to the hdf5 container
"""
Parameters
----------

lat:float32
    Inpute lattitude to be converted
lon:float32
    input longitude to be converted 
lat0:float32
    datum
lon0:float32
    datum
az:float32
    Azimuth
ylenght:float32
    The distance in meters on the y side of the model
    
Converts from lat/lon to grid coords (simple approximation). Taken from pySW4. Note that this function will probably work find with different floating point
precisions. This is really just here as a sample, you should be providing the program with a grid to begin with
Thank You to pySW4 for this function
"""

def simpleLonLatToXY(lat,lon,lat0,lon0,az,m_per_lat=111319.5, xLength=35000,m_per_lon=None):
    az_ = np.radians(az)
    if m_per_lon:
        x = (m_per_lat * np.cos(az_) * (lat - lat0)
             + m_per_lon * (lon - lon0) * np.sin(az_))
        y = (m_per_lat * -np.sin(az_) * (lat - lat0)
             + m_per_lon * (lon - lon0) * np.cos(az_))
    else:
        x = (m_per_lat * (np.cos(az_) * (lat - lat0)
                          + (np.cos(np.radians(lat)) * (lon - lon0)
                             * np.sin(az_))))
        y = (m_per_lat * (-np.sin(az_) * (lat - lat0)
                          + np.cos(np.radians(lat)) * (lon - lon0)
                          * np.cos(az_)))
    #note that I took this function from pySW4 and there it was written such that
    #its y is my x, very confusing took me a while to figure that out
    return y,xLength-x

"""
    Disscussion on HDF5 Data layout
    
    The function creates and HDF5 complient file based on the grid size aritculated in the grid.ini file. It is currently SERIAL
    but written with dask primitives, so it should be possible to parallelize file io in phase 2 of this project.
    THIS CLASS IS DESIGNED TO CREATE THE FILE use gridFile class to read grid files!
    Parameters
    ----------
     fname: str
        Name of the output file

     iniFname: str
        Name of the ini file that describes the HDF5 data structure that is going to be constructed
        
"""

def genGridFile(fname = "renoGrid.hdf5",iniFname = "grid_file.ini"):
    #load the ini construction file
    with open(iniFname,'r') as fileObject:
        ini = [line.strip() for line in fileObject if("#" not in line.strip())]
    ini = json.loads(r''.join(ini))
    #create hdf5 grid file
    #note that flipping x and y IS NOT A MISTAKE!
    y = da.linspace(0,ini["NX"]*ini["DX"],ini["NX"],chunks =(ini["CHUNKX"],)).astype(np.int32)
    x = da.linspace(0,ini["NY"]*ini["DY"],ini["NY"],chunks=(ini["CHUNKY"],)).astype(np.int32)
    z = da.linspace(0,ini["NZ"]*ini["DZ"],ini["NZ"],chunks=(ini["CHUNKZ"],)).astype(np.int32)
    topo = da.zeros(shape=(x.shape[0],y.shape[0]),chunks=(ini["CHUNKX"],ini["CHUNKY"]))
    basinSurface = da.zeros(shape=(x.shape[0],y.shape[0]),chunks=(ini["CHUNKX"],ini["CHUNKY"]))
    #compute a dask shape
    #note that I chose to use cartesian indexing
    gridCoords = da.meshgrid(x,y,z,sparse=False,indexing='xy')
    #try flipping z -- Note that an rFile scans down from a maximum elevation to the bottom (not from bottome to top as the mesh grid does, this corrects that orientation)
    #gridCoords[2] = da.flip(gridCoords[2],axis=-1)
    #now write to the hdf5 file
    da.to_hdf5(fname,'/grid/x',gridCoords[0])
    da.to_hdf5(fname,'/grid/y',gridCoords[1])
    da.to_hdf5(fname,'/grid/z',gridCoords[2])
    #save an empty (bullshit) topography
    da.to_hdf5(fname,'/grid/topo',topo)
    #create all of the empty coordinate spaces    
    #-666 is the not interpolated, empty space flag (not to be confuesd with -999 the no value flag for sw4
    da.to_hdf5(fname,'/grid/vp',da.full(gridCoords[0].shape,-666,chunks=gridCoords[0].chunksize,dtype=np.float32).flatten())
    da.to_hdf5(fname,'/grid/vs',da.full(gridCoords[0].shape,-666,chunks=gridCoords[0].chunksize,dtype=np.float32).flatten())
    da.to_hdf5(fname,'/grid/p',da.full(gridCoords[0].shape,-666,chunks=gridCoords[0].chunksize,dtype=np.float32).flatten())
    da.to_hdf5(fname,'/grid/qp',da.full(gridCoords[0].shape,-666,chunks=gridCoords[0].chunksize,dtype=np.float32).flatten())
    da.to_hdf5(fname,'/grid/qs',da.full(gridCoords[0].shape,-666,chunks=gridCoords[0].chunksize,dtype=np.float32).flatten())
    #build a unit descriptor array
    da.to_hdf5(fname,'/grid/unit',da.full(gridCoords[0].shape,-1,chunks=gridCoords[0].chunksize,dtype=np.int8).flatten())
    #now write the config file to the hdf5 file header
    result = h5py.File(fname, 'r+')
    #there really must be a better way of doing this! This reencodes the json as ascii to remove any unicode which might be in it
    ini = [i.encode("ascii","ignore") for i in json.dumps(ini)]
    result.create_dataset('/grid/ini', (len(ini),1),'S10', ini)
    #result["ini"] = json.dumps(ini)
    #result.create_dataset('ini',dtype=np.dtype("S10"),data =json.dumps(ini))

"""
    grid
    
    Parameters
    ----------
    All that this does is correctly call the dask_array create functions needed to load this hdf5 complient grid into a dask array and provide appropriate dask array opperators
    
    fname:str
        name of the hdf5 complient grid file
    chunkX:int
        chunk size for x dim. defaults to 1000
    
    chunkY: chunk size for y dim., defaults to 1000
       chunk size for y dim. defaults to 1000 
       
    chunkZ: chunk size for y dim., defaults to 1000
       chunk size for Z dim. defaults to 1000 
    
    Note that this assumes names layed out in the grid standard, (i.e x,y,z,vp,vs,p,qp,qs,unit)
    Does not load ini contents

"""

class grid():
    def __init__(self,fname="renoGrid.hdf5",chunkX=1000,chunkY=1000,chunkZ=1000):   
        data = h5py.File(fname,mode='r+')
        self.chunkX,self.chunkY,self.chunkZ = chunkX,chunkY,chunkZ
        #data access method
        self.data = data
        self.points = True #are there points?
        self.gridTopography = True #has topography been added?
        self.topo = da.from_array(data["/grid/topo"],chunks=(chunkX,chunkY))
        self.fname = fname
        self.x=da.from_array(data["/grid/x"],chunks=(chunkX,chunkY,chunkZ))
        self.y=da.from_array(data["/grid/y"],chunks=(chunkX,chunkY,chunkZ))
        self.z=da.from_array(data["/grid/z"],chunks=(chunkX,chunkY,chunkZ))
        self.vp=da.from_array(data["/grid/vp"],chunks=(chunkX*chunkY*chunkZ))
        self.vs=da.from_array(data["/grid/vs"],chunks=(chunkX*chunkY*chunkZ))
        self.p=da.from_array(data["/grid/p"],chunks=(chunkX*chunkY*chunkZ))
        self.qp=da.from_array(data["/grid/qp"],chunks=(chunkX*chunkY*chunkZ))
        self.qs=da.from_array(data["/grid/qs"],chunks=(chunkX*chunkY*chunkZ))
        self.unit=da.from_array(data["/grid/unit"],chunks=(chunkX*chunkY*chunkZ))
        #try to load any topography that might be availbile
        try:
            self.gridTopo = da.from_array(data["/grid/topo"],chunks=(chunkX))
        except KeyError as e:
            #no topography has been added to the file yet
            print(e)
            self.gridTopography = True
        #now load the metadata
        self.mdata = data["/grid/ini"][:].tolist()
        #now flatten it (equivelent to chaining for loops)
        self.mdata = list(itertools.chain(*self.mdata))
        #and encode to ascii
        self.mdata =  json.loads(b''.join(self.mdata))
        
    """
    Clear grid
    Parameters
    ----------
    None
    
    Clears the grid part of the hdf5 file (so that it can be re-written by something like one of the regression predictors)
    
    """

    def clearGrid(self):
        del self.data["/grid/vp"]
        del self.data["/grid/vs"]
        del self.data["/grid/p"]
        del self.data["/grid/qp"]
        del self.data["/grid/qs"]
 
 
    """
    Clear Points
    Parameters
    ----------
    None
    
    Clears points part of gridfile
    
    """

    def clearPoints(self):
        
        del self.data['/points/x']
        del self.data['/points/y']
        del self.data['/points/z']
        del self.data['/points/vp']
        del self.data['/points/vs']
        del self.data['/points/p']
        del self.data['/points/qp']
        del self.data['/points/qs']
    """
    assignNewGridProperties
    Parameters
    ----------
    vp: A dask array of vp values, assumes the same for all others
    
    Assisngs new values to the grid for vp,vs etc. 
    """
 
    def assignNewGridProperties(self,vp,vs,p,qp,qs):       
        da.to_hdf5(self.fname,'/grid/vp',vp.astype(np.float32))
        da.to_hdf5(self.fname,'/grid/vs',vs.astype(np.float32))
        da.to_hdf5(self.fname,'/grid/p',p.astype(np.float32))
        da.to_hdf5(self.fname,'/grid/qp',qp.astype(np.float32))
        da.to_hdf5(self.fname,'/grid/qs',qs.astype(np.float32))
        
      
    """
    assignNewGridProperties
    Parameters
    ----------
    fname: fname, the name/path to the dem you wish to assign, saved as a text file (see the DEM example in the grid part of the tests directory)
    
    lat0: Minimum lattitude of DEM (if different than the lat0 of the grid file, if nothing is passed the program will use that information)
    
    lon0: Same as for lat0 except for longitude
    
    DX: Grid spacing in x direction (leave blank to assign to the same values as for the grid)
    
    DY: Same as DX except for DY
    
    NX: Number of points in X direction (leave blank to assign to the same values as for the grid)
    
    NY: Same as NX except for in Y direction
    
    cartetisian: If DEM is already in Cartesian Coordinates (defualts to false)
    
    interpolation:  How to interpolate if there is a mismatch between grid resolutions and DEM resolutions
    
    Saves the given DEM to the DEM part of the grid file. Note that this function assumes that points in the DEM are gridded (continous) 
    """
    
    def assignDEMToGrid(self,dem=None,lat0=None,lon0=None,DX=None,DY=None,NX=None,NY=None,interpolation="nearest",cartesian=False):
        if(type(dem) == str):
            #if the dem is a string, open the file and process it, otherwise assume that it is an numpy array input already in the correct coordinates
            dem = None
            print("assigining DEM to DEM part of grid file, NOTE this is a serial, in memory function, if there is enough demand I will improve it further")
            #make sure that we know there is grid topography
            print("Topography added, you will need to reload the class in order to access them")
            if(None in (lat0,lon0)):
                print("Assigning lat and lon 0 from from mprops ini in container")
                lat0,lon0 = self.mdata["LAT0"],self.mdata["LON0"]
            if(None in (DX,DY,NX,NY)):
                print("Assining DX,DY,NX and NY from mprops ini in container")
                DX,DY,NX,NY = self.mdata["DX"],self.mdata["DY"],self.mdata["NX"],self.mdata["NY"]
            
            #load and save to dem using numpy (serial)
            dem = np.loadtxt(fname)
            #convert lat lon
            # simpleLonLatToXY, note lonLat
            if(not(cartesian)):
                dem[:,0],dem[:,1] = simpleLonLatToXY(lat=dem[:,0],lon=dem[:,1],lat0=lat0,lon0=lon0,az=self.mdata['AZIMUTH'])
            #discard everything that is out of extent
            dem = np.array([i for i in dem if (i[0] >= 0 and i[1] >= 0)])
            #assign to grid--Since this is small I can just use the assign to grid methods given by numpy and save myself a lot of screwing around
            (x,y) = np.meshgrid(np.linspace(0,DY*NY,NY),(np.linspace(0,DX*NX,NX)),indexing='xy')
            dem = griddata((dem[:,0],dem[:,1]),(dem[:,2]),(x,y),method=interpolation,rescale=False)
            #assign
            da.to_hdf5(self.fname,'/grid/topo',da.asarray(dem.astype(np.float32)))
        #otherwise assume that this is numpy input
        else:
            if(not(cartesian)):
                print("this doesnt happen")
                lat0,lon0 = self.mdata["LAT0"],self.mdata["LON0"]
                dem[:,0],dem[:,1] = simpleLonLatToXY(lat=dem[:,0],lon=dem[:,1],lat0=lat0,lon0=lon0,az=self.mdata['AZIMUTH'])
            
            #otherwise I have been given coordinates and am ready to go--Use same resolution as grid
            DX,DY,NX,NY = self.mdata["DX"],self.mdata["DY"],self.mdata["NX"],self.mdata["NY"]
            (x,y) = np.meshgrid(np.linspace(0,DY*NY,NY),(np.linspace(0,DX*NX,NX)),indexing='xy')
            dem = griddata((dem[:,0],dem[:,1]),(dem[:,2]),(x,y),method=interpolation,rescale=False)           
            #clear the exsisting points since they are in the wron orientation
            del self.data['/grid/topo']
            da.to_hdf5(self.fname,'/grid/topo',da.asarray(dem.astype(np.float32)))

"""
surfaces

This class is desinged to hold abstract surfaces in order to evaluate special functions over subsets of the rfile
Includes helper functions to compute the appropriate areas to opperate on (designed for say applying a specific function to only the 
basin or for evaluating along a fault or some other similar kind of problem)

Parameters
---------

gridObj:grid
    open grid object to manipulate
dataSet:str
    Name or other identifier for this dataset (to be used with the HDF5 container and added to the data sets list)
dataType:str
    Data type flag, options include s (surface) or v (volume)

"""
class surfaces():
    def __init__(self,gridObj,dataSet,comment=None,dataType=None,surface=None,overwrite=False):
        self.grid = gridObj
        points=True
        self.dataSet = dataSet
        self.dataType=dataType
        #does this data set exist?
        #load all existing data sets
        try:
            if(overwrite):
                #Case overwrite exsisting data set
                #delete the existing data set
                del self.grid.data['/geometeries/surfaces/' + dataSet]
                #overwrite it with the new data
                try:
                    self.saveSurface(dataSet,comment,dataType,surface)
                except Exception as e:
                    print("tried to include null points?")
                    print(repr(e))
                pass
                
            elif(dataSet in self.grid.data['/geometeries/surfaces/'].keys() and not(overwrite) and dataType != None ):
                print("this data set already exsists, set overwrite=True to overwrite")
        
        #this will only be called if the data set doesnt exist
        except KeyError as e:
            try:
                #save the new data set
                print("trying to save data set!")
                self.saveSurface(dataSet,comment,dataType,surface)
            except Exception as e:
                print("tried to include null points?")
                print(repr(e))
            pass
            
        #finally load the points
        self.loadSurface()
    
    """
    Function savePoints:
    saves points to the hdf5 data structure (called by constructor)
    """
    def saveSurface(self,dataSet,comment,dataType,surface):
        chunk_size = surface.shape
        #create the group for the new data set
        self.grid.data.create_group('geometeries/surfaces/'+dataSet)
        #save the dataType metedata
        self.grid.data['geometeries/surfaces/'+dataSet].attrs['dataType'] = dataType
        #save all other metadata
        self.grid.data['geometeries/surfaces/'+dataSet].attrs['comment'] = comment
        #save the surface
        da.to_hdf5(self.grid.fname,'geometeries/surfaces/'+dataSet + '/surface',da.from_array(surface,chunks=chunk_size))
        
    
    """
    Function Load Points:
    loads points from the hdf5 container (if availible) for the given data set, designed to be used internally by constructor
    """
    def loadSurface(self):

        dataSet = self.dataSet
        data = self.grid.data
        try:
            self.surface=da.from_array(data['geometeries/surfaces/' + dataSet + "/"+"surface"],chunks=data['geometeries/surfaces/' + dataSet + "/"+"surface"].shape)
            self.comment = data['geometeries/surfaces/'+dataSet].attrs['comment']
            self.dataType = data['geometeries/surfaces/'+dataSet].attrs['dataType']
        except KeyError as e:
            raise KeyError
    
    """
    Function getPoints:
    returns an "pointer" to all points heald within the object
    """
    def getPoints(self):
        return da.stack((self.surface,self.unit,self.comment,self.dataType))


"""
volume

This class evaluates volumes between given input surfaces and uses this information to evaluate functions within those volumes for the grid

Parameters
---------

gridObj:grid
    open grid object to manipulate

surfacesDic:Dictionary
    Dictionary containing all input surfaces

"""


class volume():
    def __init__(self,gridObj,surfacesDic):
        self.gridfile = gridObj
        self.surfacesDic = surfacesDic

    #computes an dask bool array containing the volumes bounded by the two input surfaces
    def computeEvalVolume(self,topSurface=None,bottomSurface=None,datum=None):
        if(datum==None):
            #assign dataum from grid file
            datum = self.gridfile.mdata["datum"]
        topSurface = self.surfacesDic[topSurface].surface
        topSurface = topSurface + datum
        bottomSurface = self.surfacesDic[bottomSurface].surface
        bottomSurface = bottomSurface +datum
        topEvalSurface = []
        bottomEvalSurface = []
        volume = []
        #do it one complete layer at a time looping downward, evaluate first layer
        for i in range(self.gridfile.z.shape[2]-1,-1,-1):
            #removalIndex.append(self.gridObj.z[:,:,i] >= (topo))
            topEvalSurface = self.gridfile.z[:,:,i] <= (topSurface)
            bottomEvalSurface = self.gridfile.z[:,:,i] >= (bottomSurface)
            volume.append(topEvalSurface & bottomEvalSurface)
        #flatten into a single dask array
        volume = da.stack(volume,axis=-1)        
        volume = volume.flatten()
        return volume
        
    ### evalutes a function on the given surface returns a dask array to create the new grid for that object
    ### the rechunk opperator is to have the code chunk everything correctly (but in an automatic and potentiall ineffeient way)
    
    def evalOn(self,values,volumeIndexes,x,y,z,opperator,rechunk=True):
        if(rechunk):
            x = x.rechunk({0: -1, 0: 'auto'},block_size_limit=1e6)
            y = y.rechunk(x.chunks)
            z = z.rechunk(x.chunks)
            values = values.rechunk(x.chunks)
            volumeIndexes = volumeIndexes.rechunk(x.chunks)
            
        #make sure that this will actually work--Chunks and lengths must be the amse
        assert x.numblocks == y.numblocks == z.numblocks == values.numblocks == volumeIndexes.numblocks
        return da.map_blocks(self.evalOnBlock,x,y,z,values,volumeIndexes,opperator,dtype=values.dtype)            
        
    @staticmethod
    #should not have to use this externally
    #but basically just takes the volume indexes and the sklearn predictor and calculates only in that space
    #values is the current value (such as vp or vs)
    def evalOnBlock(x,y,z,values,volumeIndexes,opperator):
        x=x.ravel()
        y=y.ravel()
        z=z.ravel()        
        ### see if I need to do anything
        if(True not in volumeIndexes):
            return values
        """
        At some point build a version of this method that evaluates points in groups and assigns in groups since that will be 
        a lot faster than this, also look at the task graph sometime to see if that actually matters (or if it is smart enough to deal with this)
        """
        for i in range(len(values)):
            if(volumeIndexes[i]==True):
                # since this is only one value no axis! values[i] = opperator.fit(np.stack([x[i],y[i],z[i]],axis=1))
                values[i] = opperator.predict(np.stack([x[i],y[i],z[i]]).reshape(1, -1))
                #values[i]=-500.0 #verify that this works
        return values


        
"""
    points
    Parameters
    ----------
    
    gridObj:grid
        open grid object to manipulate
    dataSet:str
        Name or other identifier for this dataset (to be used with the HDF5 container and added to the data sets list)
    dataType:str
        Data type flag, options include s (surface) (for something like gravity data), l (line) (for something like an remi profile or for well data)
        or v (volume) (for example if you have an nice rendering of the material property model or something...)
    comment:str
        Any other stuff you would like to save (I use this to just dump an copy of the whole remi record)
    x:nd array
        x coordinate points
    y:nd array
        y coordinates for the points
    z:nd array
       z coordinates for the points
    vp:nd array
        corresponding vp values
    vs:nd array
        corresponding vs values
    p:nd array
        corresponding p values 
    qp:nd array
        corresponding qp values 
    qs:nd array
        corresponding qs values 
    overwrite:Bool
        Do you want to overwrite points that may already be in the hdf5 container?
    uses dx dy dz and carteisian input coordinates to compute the coordinates needed for the hdf5 volume.
    These values are then saved in the /grid/ section of the hdf5 container
    
    Object for holding the points of an specific data set
    Note that this is not supposed to be an sophisticated class, merely an nice container for this stuff
    I plan to convert all of these to dask compatible objects if and when that sort of storage is required

"""

class points():
    def __init__(self,gridObj,dataSet,comment=None,dataType=None,x=None,y=None,z=None,unit=None,vp=None,vs=None,p=None,qp=None,qs=None,overwrite=False):
        self.grid = gridObj
        points=True
        self.dataSet = dataSet
        self.dataType=dataType
        #does this data set exist?
        #load all existing data sets
        try:
            if(overwrite):
                #Case overwrite exsisting data set
                #delete the existing data set
                del self.grid.data['/points/' + dataSet]
                #overwrite it with the new data
                try:
                    self.savePoints(dataSet,comment,dataType,x,y,z,unit,vp,vs,p,qp,qs)
                except Exception as e:
                    print("tried to include null points?")
                    print(repr(e))
                pass
                
            elif(dataSet in self.grid.data['points'].keys() and not(overwrite) and dataType != None ):
                print("this data set already exsists, set overwrite=True to overwrite")
        
        #this will only be called if the data set doesnt exist
        except KeyError as e:
            try:
                #save the new data set
                self.savePoints(dataSet,comment,dataType,x,y,z,unit,vp,vs,p,qp,qs)
            except Exception as e:
                print("tried to include null points?")
                print(repr(e))
            pass
            
        #finally load the points
        self.loadPoints()
    
    """
    Function savePoints:
    saves points to the hdf5 data structure (called by constructor)
    """
    def savePoints(self,dataSet,comment,dataType,x,y,z,unit,vp,vs,p,qp,qs):
        ### require that all flat arrays use gridX chunk size
        chunk_size = self.grid.chunkX
        #create the group for the new data set
        self.grid.data.create_group('points/'+dataSet)
        #save the dataType metedata
        self.grid.data['points/'+dataSet].attrs['dataType'] = dataType
        #save all other metadata
        self.grid.data['points/'+dataSet].attrs['comment'] = comment
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/x',da.from_array(x,chunks=chunk_size))
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/y',da.from_array(y,chunks=chunk_size))
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/z',da.from_array(z,chunks=chunk_size))
        #save the unit descriptor to the grid file--Note that I am seriously thinking of throwing this out since I dont seem to need it anymore
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/unit',da.from_array(unit,chunks=chunk_size))
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/vp',da.from_array(vp,chunks=chunk_size))
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/vs',da.from_array(vs,chunks=chunk_size))
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/p',da.from_array(p,chunks=chunk_size))
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/qp',da.from_array(qp,chunks=chunk_size))
        da.to_hdf5(self.grid.fname,'points/'+dataSet + '/qs',da.from_array(qs,chunks=chunk_size))
        pass
    
    """
    Function Load Points:
    loads points from the hdf5 container (if availible) for the given data set, designed to be used internally by constructor
    """
    def loadPoints(self):
        chunkX= self.grid.chunkX,
        dataSet = self.dataSet
        data = self.grid.data
        try:
            self.x=da.from_array(data["/points/" + dataSet + "/"+"x"],chunks=chunkX)
            self.y=da.from_array(data["/points/" + dataSet + "/"+"y"],chunks=chunkX)
            self.z=da.from_array(data["/points/" + dataSet + "/"+"z"],chunks=chunkX)
            self.vp=da.from_array(data["/points/" + dataSet + "/"+"vp"],chunks=chunkX)
            self.vs=da.from_array(data["/points/" + dataSet + "/"+"vs"],chunks=chunkX)
            self.p=da.from_array(data["/points/" + dataSet + "/"+"p"],chunks=chunkX)
            self.qp=da.from_array(data["/points/" + dataSet + "/"+"qp"],chunks=chunkX)
            self.qs=da.from_array(data["/points/" + dataSet + "/"+"qs"],chunks=chunkX)
            self.unit=da.from_array(data["/points/" + dataSet + "/"+"unit"],chunks=chunkX)
            self.comment = data['/points/'+dataSet].attrs['comment']
            self.dataType = data['/points/'+dataSet].attrs['dataType']
        except KeyError as e:
            raise KeyError
    
    """
    Function getPoints:
    returns an "pointer" to all points heald within the object
    """
    def getPoints(self):
        return da.stack((self.x,self.y,self.z,self.vp,self.vs,self.p,self.qp,self.qs))

###Currently all mprops stuff is merely commented out since I am not planing on actually using any of it

class materialProperties():
    def __init__(self,gridObj,mpropsINI=""):
        print("only use this class if you injected points WITHOUT material properties!")
        self.gridObj = gridObj
        if(mpropsINI!=""):
            #add mprops
            #self.addMpropsINI(mpropsINI)
            pass
        #load mprops from hdf5 file
        #self.mdata = self.loadMprops()
        pass
        
    """
    Parameters
    ----------
    mpropsINI:str 
        location of the mrpops.ini file which descirbes that materials assigned for a particular unit
    Assigns material properties metadata section of points part of hdf5 container
    """
    def addMpropsINI(self, mpropsINI):
        #adds and computes mprops for all data in points part of hdf5 struct.
        with open(mpropsINI,'r') as fileObject:
            mpropsINI = [line.strip() for line in fileObject if("#" not in line.strip())]
        mpropsINI = json.loads(r''.join(mpropsINI))
        #save this metadata to the appropriate section of the hdf5 file
        try:
            self.gridObj.data.create_dataset('/points/mprops', (len([i.encode("ascii","ignore") for i in json.dumps(mpropsINI)]),1),
            'S10', [i.encode("ascii","ignore") for i in json.dumps(mpropsINI)])
        
        except RuntimeError as e:
            print("overwriting exisitng mprops ini in points/mprops")
            del self.gridObj.data['/points/mprops']
            self.gridObj.data.create_dataset('/points/mprops', (len([i.encode("ascii","ignore") for i in json.dumps(mpropsINI)]),1),
            'S10', [i.encode("ascii","ignore") for i in json.dumps(mpropsINI)])
    """
    Loads all material properties from the points part of the hdf5 compliant grid container
    Note that this functionality isn part of gridObj because it is literally only used here
    """
    def loadMprops(self):
        #do the same for points (mprops)
        mdata = self.gridObj.data["/points/mprops"][:].tolist()
        mdata = list(itertools.chain(*mdata))
        return json.loads(b''.join(mdata))
    
    """
    Assign mprops from coordinate file    
    Basically loads up an ascii formated text file with the correct x,y,z coordinates and material properties and adds to the points part of
    the file
    """
    def assignFromCoordFile(self):
        
        
        
        pass
    """
    Assigns material properties based off of description in points/mprops
    Note that this will always overwrite the exsisting material properties with the new ones
    This should be removed from this progrma and just made into a jupyter notebook that someone uses to make inputs
    it realy is out of place
    """
    def assignMprops(self):
        #assign static, figure out dynamic assignment later
        static = True
        if(static):
            for units in self.mdata["UNITS"].keys():
                #load up the current grid obj
                print(units)
                vp= da.from_array(self.gridObj.data["/points/vp"],chunks=(self.gridObj.pointx.chunksize))
                vs=da.from_array(self.gridObj.data["/points/vs"],chunks=(self.gridObj.pointx.chunksize))
                p=da.from_array(self.gridObj.data["/points/p"],chunks=(self.gridObj.pointx.chunksize))
                qp=da.from_array(self.gridObj.data["/points/qp"],chunks=(self.gridObj.pointx.chunksize))
                qs=da.from_array(self.gridObj.data["/points/qs"],chunks=(self.gridObj.pointx.chunksize))
                #where is there a valid unit that matches the current unit or one that hasnt been assigned?
                unitAssignments = da.where(da.logical_and(self.gridObj.pointunit==int(units),vp==-666),True,False)
                #note that unit assignment is NOT a list of indexes as you would normally expect, it behaves more like 
                # a np.where operator which is why I need to reset it before each assignment
                vp[unitAssignments] = self.mdata["UNITS"][units]["VP"]
                unitAssignments = da.where(da.logical_and(self.gridObj.pointunit==int(units),vs==-666),True,False)
                vs[unitAssignments] = self.mdata["UNITS"][units]["VS"]
                unitAssignments = da.where(da.logical_and(self.gridObj.pointunit==int(units),p==-666),True,False)
                p[unitAssignments] = self.mdata["UNITS"][units]["P"]
                unitAssignments = da.where(da.logical_and(self.gridObj.pointunit==int(units),qp==-666),True,False)
                qp[unitAssignments] = self.mdata["UNITS"][units]["QP"]
                unitAssignments = da.where(da.logical_and(self.gridObj.pointunit==int(units),qs==-666),True,False)
                qs[unitAssignments] = self.mdata["UNITS"][units]["QS"]

                #save all of the changes to the arrays (for this cycle)
                da.to_hdf5(self.gridObj.fname,"/points/vp",vp)
                da.to_hdf5(self.gridObj.fname,"/points/vs",vs)
                da.to_hdf5(self.gridObj.fname,"/points/p",p)
                da.to_hdf5(self.gridObj.fname,"/points/qp",qp)
                da.to_hdf5(self.gridObj.fname,"/points/qs",qs)
        #done
        #TODO add non static parts (which will involve assigning to a statistical distribution instead of to a value)
    
    def cutOffAtDEM(self,assign=True):
        topo = self.gridObj.topo + self.gridObj.mdata["datum"]
        #topo = da.flipud(topo)
        removalIndex = []
        #verify that there is presently a DEM
        if(not(self.gridObj.gridTopography)):
            print("no dem present in grid file, please assign one to continue")
            return 
        #do it one complete layer at a time looping downward
        for i in range(self.gridObj.z.shape[2]-1,-1,-1):
            #the greater than is because the indexing of the rFile is flipped from whay you would expect
            #the transposition is to deal with the fact that the 2d mesh grid is flipped reletive to the 3d one
            removalIndex.append(self.gridObj.z[:,:,i] >= (topo))
        #join into a single dask array
        removalIndex = da.stack(removalIndex,axis=-1)        
        removalIndex = removalIndex.flatten()
        #drop values
        self.gridObj.vp[removalIndex] = -999
        self.gridObj.vs[removalIndex] = -999
        self.gridObj.p[removalIndex] = -999
        self.gridObj.qp[removalIndex] = -999
        self.gridObj.qs[removalIndex] = -999
        if(assign):
            print("assiging dem cut off to gridfile")
            self.gridObj.assignNewGridProperties(self.gridObj.vp,self.gridObj.vs,self.gridObj.p,self.gridObj.qp,self.gridObj.qs)

    """
    assignPropertiesToRegion
    Parameters
    ----------

    vp:P velocity predictor
    
    vs:Shear velocity predictor
    
    p: density predictor
    
    qp: p wave attenuation predictor
    
    qs:shear wave attenuation predictor

    topSurface: dask array containing the extent of the top surface
    
    bottomSurface: dask array for bottom boundary to evaluate 
    
    interpolate: Bool attempt to interpolate if the top and bottom surface are different sizes (WARNING: non parallel, uses numpy, must fit in memory)
    
    interpolation: str defaults to LINEAR, if interpolating what kind of interpolation do I preform?

    Similar to cut off at DEM except assigns material between DEM and something else
    Assigns properties to a particular region of the grid (for example, if I want to evaluate the basin and the bedrock differently, I could first construct the bedrock model and then evaluate this function within
    the basin only by evalauating in between the top surface (DEM) and the bottom surface (the basin topology).
    Note that the top and the bottome surfaces must have the same extents!
    """ 
    
    def assignPropertiesToRegion(self,topSurface,bottomSurface,vp,vs,p,qp,qs):
        # check that th
        
        print("assignProperteisToRegion called")
        pass
