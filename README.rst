===============================
pointsToRfile
===============================


In the course of looking for employment I have received several requests for code examples. This is an old library which I can publicaly release that I used to develop 3d material property models
for use with sw4, an earthquake hazard modeling tool, for use with my masters thesis.

I built this library using a cookiecutter template to provide methods for taking point data, inserting it into the grid hdf5 data format, interpolating on this and saving the results as an rFile ( a type of binary file that sw4 can read material models from).
I had originally intended to develop this into a library to share with other seismologists whom are using sw4 in their work. Since there was little interest I ended up just
using it to make the material property models I present in my masters thesis. Sw4 later added direct support for hdf5 containers (through the sfile) which further 
obviates many features that this library provides. 

This library still serves as a good demonstration of my programming ability and problem solving approach. The key module is the grid class (located in https://github.com/firstkingofrome/pointsToModel/blob/master/points2Rfile/grid/grid.py , all of which is written by me except for the 
simpleLonLatToXY function which I credit to sw4). I have also included a few jupyter notebooks which run this library to generate a model using a simple knn scheme
with sklearn. 

Due to the lack of interest I never got added automatic tox tests or documentation generation (I am familiar with unit testing and would unit test in any situation where I was developing production software with others).

===============================
installation
===============================

1. Set up an anaconda enviroment using the env.yaml file: conda env create -f env.yaml

2. Install the libary localy (I recomend using pip in editable mode): pip install -e .

3. The notebooks in examples should now work
