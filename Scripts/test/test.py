import arcpy
import json

debug = True

def log_message(msg, level="message"):
    level = level.strip().lower()
    if level == "message":
        arcpy.AddMessage(msg)
    elif level == "warn":
        arcpy.AddWarning(msg)
    elif level == "error":
        arcpy.AddError(msg)
    print msg

if __name__ == "__main__":

    inSR = 102100
    
    #inSR = '{"wkid":102100}'
    #inSR = '{"wkt" : "GEOGCS[\\"GCS_WGS_1984\\",DATUM[\\"D_WGS_1984\\",SPHEROID[\\"WGS_1984\\",6378137,298.257223563]],PRIMEM[\\"Greenwich\\",0],UNIT[\\"Degree\\",0.017453292519943295]]"}'
    #{"wkt" : "GEOGCS[\"GCS_WGS_1984\",DATUM[\"D_WGS_1984\",SPHEROID[\"WGS_1984\",6378137,298.257223563]],PRIMEM[\"Greenwich\",0],UNIT[\"Degree\",0.017453292519943295]],PROJECTION[\"Mercator_Auxiliary_Sphere\"],PARAMETER[\"False_Easting\",0.0],PARAMETER[\"False_Northing\",0.0],PARAMETER[\"Central_Meridian\",0.0],PARAMETER[\"Standard_Parallel_1\",0.0],PARAMETER[\"Auxiliary_Sphere_Type\",0.0],UNIT[\"Meter\",1.0],AUTHORITY[\"ESRI\",\"102100\"]]"}
    {"wkt" : "GEOGCS[\"GCS_WGS_1984\",DATUM[\"D_WGS_1984\",SPHEROID[\"WGS_1984\",6378137,298.257223563]],PRIMEM[\"Greenwich\",0],UNIT[\"Degree\",0.017453292519943295]]"}
    
    defaultSR = None

    try:
        # User can just specify the number
        wkid = int(inSR)
        defaultSR = arcpy.SpatialReference()
        defaultSR.factoryCode = wkid
        defaultSR.create()
    except ValueError:
        # Not an int; try to parse the String as Json
        print inSR
        inSR = inSR.replace("\\\\","\\")
        print inSR
        SR = json.loads(inSR)

        if not SR is None:
            # Create spatial ref from service response        
            defaultSR = arcpy.SpatialReference()
            try:
                defaultSR.factoryCode = SR['wkid']
                defaultSR.create()
            except KeyError:
                if debug: log_message("Default Spatial reference has no wkid")
                try:
                    defaultwkt = SR['wkt']
                    defaultSR.loadFromString(defaultwkt)
                except:
                    if debug: log_message("Default Spatial reference has no wkt")
                    raise Exception("Could not set the Default Spatial Reference")
                    


    geomJSON = '{"rings":[[[-10124008.08980318,4710187.298721861],[-10108873.55820271,4719206.868059516],[-10085025.205377726,4721805.727021213],[-10065915.948306425,4719665.490229227],[-10049252.67614025,4710798.794948143],[-10040844.603028877,4700250.485044785],[-10035188.262935773,4687409.06429287],[-10060871.104439601,4667535.436938717],[-10069126.303494403,4676096.384106659],[-10068361.933211552,4697193.0039133765],[-10082426.346416028,4706059.69919446], [-10092057.411979964,4710187.298721861],[-10101994.225657042,4699944.736931643],[-10090681.54547083,4683434.33882204],[-10112695.40961697,4675790.635993519],[-10128135.689330582,4693676.9006122565],[-10124008.08980318,4710187.298721861]]]}'

    inGeom = json.loads(geomJSON)

    point = arcpy.Point()
    sub_array = arcpy.Array()
    array = arcpy.Array()

    coordList = inGeom['rings']

    j = 0

    for coord in coordList:
        k = 0
        for coordPair in reversed(coord):                        
            k += 1
            point.X = coordPair[0]
            point.Y = coordPair[1]                        
            sub_array.add(point)
        array.append(sub_array)
        
        sub_array.removeAll()
        j += 1

    if defaultSR is None:
        print "No SR defined"
        clipPoly = arcpy.Polygon(array)        
    else:                        
        clipPoly = arcpy.Polygon(array, defaultSR)  

    clipfc = arcpy.CreateFeatureclass_management(r'in_memory', "clip", "POLYGON", '#', 'DISABLED', 'DISABLED', defaultSR)

    print clipfc

    
    

