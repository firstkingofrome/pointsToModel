===============================
Examples
===============================

This directory contains scripts to build a simple material property model. Due to the size (~250 Mb) I do not include the renoRemi100m.hdf5 file in the github repository. Running the notebooks in the following order will regenerate it:

addBasinAndDEM.ipynb
---------------------
* This generates and empty grid file containing surfaces for the surface (as defined in the AL_DEM file) and the basin elevation (as defined by the surface described in alKrigged100M.txt

* Horizontal and vertical resolutions as well as spatial information (such as the location of this material model) are defined in
100m.ini. This file also controls chunking (and ultimately) the resolution to interpolate to when building the grid

addRemiToGrid.ipynb
-------------------

* Takes points measured using ReMi (a technique which uses ambient noise to estimate the shear wave velocity at a location) within the Reno basin and saves them as a point data set for use with sklearn estimators

generateFromKneighbors.ipynb
----------------------------

* This script shows how to use sklearn estimators to generate a simplified material property model (in this case just by using k nearest neighbors)

* It also shows how to use the PointsToModels library to remove (in parallel) erroneous data which exists above the boundary defined by the DEM and how to convert a coords hdf5 container to an sw4 compliant rfile.

Rendering with paraview:
------------------------

I have develoepd a script to render these models with paraview (which provides an excellent way to see how well sklearn is working). I published this as part of a paper
and am unsure if I am allowed to include it here, however you can download it by following this link to my papers electronic suplement: https://gsw.silverchair-cdn.com/gsw/Content_public/Journal/bssa/112/1/10.1785_0120200309/3/bssa-2020309_supplement_fullresolutionmaterialmodel_paraview.zip?Expires=1657648114&Signature=4CKp0xBzFoVXDzXqDKU0c2UZZztFAI4iGVbNXIzcL3bmQmikmkY1A0pqGDUjytvpjTOZSRUx37jNpq6oUZ7mI2eGypZ-CA~3sThPjBWy9TKXxI0FEMsXZTzic8As36-bZSojeO1J5eAaJppsKlml9lLhj7D4Skpvh8jMS-odvgrdQslwENO8WVTaLzVV0z03I-dkbp37yvWFnwdebkmiGa-5u39voI1yj81o237g7x6BLJ6Wrzxv6jrSnhdqAeJo6JFFBDvrdd~fxmkknoKlfYzHnkDf4nx5qv-XL5Nl7VHekHQ6DbuwzS5HoT3vviW1WBmYHJbIyhAYzLIAsOH9Sw__&Key-Pair-Id=APKAIE5G5CRDK6RD3PGA

Here is a link to the complete paper: https://pubs.geoscienceworld.org/ssa/bssa/article/112/1/457/608573/Exploring-Basin-Amplification-within-the-Reno
