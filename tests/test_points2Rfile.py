#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_points2Rfile
----------------------------------
Tests for `points2Rfile` module.
"""

print("not yet configured with tox, please call manually!")
import unittest
import points2Rfile.grid

def testModule():
    points2Rfile.grid.genGridFile()
    mpropsINI = "mprops.ini"
    pointFnames = ["asciiExample.txt","asciiTwo.txt"]
    gridFile = points2Rfile.grid.grid("renoGrid.hdf5")

    print("make point injecture concious of the datum, at some point")
    pointInjecture = points2Rfile.grid.injectPoints(gridFile)
    pointInjecture.injectAsciiWGS84(pointFnames)

    #refresh the grid file object with the points you added
    gridFile = points2Rfile.grid.grid("renoGrid.hdf5")
    self = points2Rfile.grid.materialProperties(gridFile,mpropsINI)
    # add material properties
    self.assignMprops()

def testAssignDEM():
    #test DEM
    gridFile = points2Rfile.grid.grid("renoGrid.hdf5")
    gridFile.assignDEMToGrid()
    gridFile = points2Rfile.grid.grid("renoGrid.hdf5")

def testCutOffDEM():
    gridFile = points2Rfile.grid.grid("renoGrid.hdf5")
    self = points2Rfile.grid.materialProperties(gridFile)
    self.cutOffAtDEM()


class TestPoints2rfile(unittest.TestCase):

    def setUp(self):
        pass

    def test_something(self):
        assert(points2Rfile.__version__)

    def tearDown(self):
        pass
