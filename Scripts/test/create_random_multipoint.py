import arcpy

from arcpy import env

env.overWriteOutput = True

env.outputCoordinateSystem = "Coordinate Systems/Geographic Coordinate Systems/World/WGS 1984.prj"

numExtent = "-180 -90 180 90"
numFeatures = 1000
numPointsPerFeatures = 5

arcpy.CreateRandomPoints_management(r'C:\agsresources\vector\rsstest\data\rsstest.mdb', 'multipoint','#',numExtent,numFeatures,'#',"MULTIPOINT",numPointsPerFeatures)
