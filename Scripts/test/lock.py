import arcpy

def testme():

    output_folder = r"C:\Temp"


    fcSR = arcpy.SpatialReference()
    fcSR.factoryCode = 4326
    fcSR.create()

    geomType = "POLYGON"

    #db = arcpy.CreateFileGDB_management(output_folder,"export","9.3")
    #fc = arcpy.CreateFeatureclass_management(db, "output", geomType, '#', 'DISABLED', 'DISABLED', fcSR)

    fc = arcpy.CreateFeatureclass_management(output_folder, "test", geomType, '#', 'DISABLED', 'DISABLED', fcSR)

    
    iCur = arcpy.InsertCursor(fc)

    feat = iCur.newRow()

    del feat
    del iCur
    # This works for File DB, Persoanl DB, and Shapefiles
    try:
        db = arcpy.CreatePersonalGDB_management("in_memory","export2","9.3")
    except:
        print "OK"
    


if __name__ == "__main__":
    testme()
