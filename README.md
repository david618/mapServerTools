### mapServerTools

ArcGIS Toolbox for Exporting Map Service data to Shapefile, Personal GeoDB,  or File GeoDatabase.

Shapefile do not support null values.   They come in as None from JSON and you have to force them to some default value for int, date, etc. [Geoprocessing considerations for shapefile output](http://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#//002t0000000m000000.htm)

Two toolboxes.  One is intended for use via ArcCatalog/Desktop the other can be deployed as a GP Tool.

I justed tested and the Desktop tool still works at 10.5.
