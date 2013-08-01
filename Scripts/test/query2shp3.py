import arcpy
import urllib
import json
import datetime
from time import gmtime, strftime

'''

Query for Line Features
http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/1/query?where=1%3D1+and+objectid+%3C+100&returnGeometry=true&outFields=&f=pjson

Query for Polygon Features
http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/2/query?where=OBJECTID+%3C+100&returnGeometry=true&outFields=*&f=pjson

Query for Point Features
http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/4/query?where=OBJECTID+%3C+200&returnGeometry=true&outFields=*&f=pjson

input will be a query URL


'''

if __name__ == '__main__':

    iCur = arcpy.Cursor

    time_fmt = "%a, %d %b %Y %H:%M:%S" 
    
    try:


        print "Start: " + strftime(time_fmt, gmtime())
        output_folder = r"C:\Temp"
        output_shapefilename = r"test1.shp"


        # line
        #query_url = r"http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/1/query?where=objectid+%3C+100&returnGeometry=true&outFields=*&f=pjson"
        
        # polygon
        query_url = r"http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/2/query?where=OBJECTID+%3C+100&returnGeometry=true&outFields=*&f=pjson"
        #query_url = r"http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/2/query?where=1%3D1&returnGeometry=true&outFields=*&f=pjson"
        #query_url = r"http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/2/query?where=OBJECTID%3D409&returnGeometry=true&outFields=*&f=pjson"
        #query_url = r"http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/2/query?where=OBJECTID%3D409&returnGeometry=true&outFields=*&f=pjson&maxAllowableOffset="
        
        # point
        #query_url = r"http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/4/query?where=OBJECTID+%3C+200&returnGeometry=true&outFields=*&f=pjson"

        # multipoint
        #query_url = r"http://12.187.20.60/stlgis/rest/services/vector/rsstest2/MapServer/5/query?where=OID+%3C+100&returnGeometry=true&outFields=*&f=pjson"

        '''
        f = {}
        f['where'] ='1=1 and objectid < 100'
        f['returnGeometry'] = 'true'
        f['outFields'] = '*'
        f['f'] = 'pjson'
        
        params = urllib.urlencode(f)
        print params
        
        query_url = r"http://12.187.20.60/stlgis/rest/services/vector/rsstest/MapServer/1/query?" + params
        print query_url
        '''

        
                
        resp = json.load(urllib.urlopen(query_url))

        displayFieldName = resp['displayFieldName']
        fieldAliases = resp['fieldAliases']
        geometryType = resp['geometryType']
        spatialReference = resp['spatialReference']
        fields = resp['fields']
        features =  resp['features']

        geomType = "POINT"
        if geometryType == "esriGeometryPolyline":
            geomType = "POLYLINE"
        elif geometryType == "esriGeometryPolygon":
            geomType = "POLYGON"
        elif geometryType == "esriGeometryMultipoint":
            geomType = "MULTIPOINT"
            
        
        

        fcSR = arcpy.SpatialReference()
        fcSR.factoryCode = spatialReference['wkid']
        fcSR.create()
        
        inFields = []
        tfnames = []
        for field in fields:
            print field['name'] + " : " + field['type'] + " : " + field['alias']
            fname = field['name']
            tfname = fname

            if len(fname) > 10:
                fname8 = fname[0:8]
                for fx in "123456789abcdefghijklmnopqrstuvwxyz":
                    tfname = fname8 + "_" + fx
                    try:
                        tfnames.index(tfname)
                    except ValueError as e:
                        # Value not found ok to append
                        break;
            tfnames.append(tfname)                                                                                         
            
            if field['type'] == 'esriFieldTypeString':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': field['length'], 'type':'TEXT', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeDouble':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'DOUBLE', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeDate':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': field['length'], 'type':'DATE', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeSmallInteger':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'SHORT', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeInteger':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'LONG', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeFloat':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'FLOAT', 'alias':field['alias']})            
 

        arcpy.env.workspace = output_folder
        
        try:
            arcpy.Delete_management(output_shapefilename)
        except Exception as e:
            print e

        fc = arcpy.CreateFeatureclass_management(output_folder, output_shapefilename, geomType, '#', 'DISABLED', 'DISABLED', fcSR)

        print fc

        field_count = 0
        has_id_field = False
        unlikely_fc_name = 'qetuop0987'
        for field in inFields:
            if field['tfname'].upper() == "ID":
                has_id_field = True
                if field_count == 0:
                    # Add a temp field with a name that is unlikely to collide
                    arcpy.AddField_management(fc, unlikely_fc_name , 'LONG', '#', '#', 0)
                arcpy.DeleteField_management(fc, 'ID')                                    

            arcpy.AddField_management(fc, field['tfname'][:10], field['type'], '#', '#', field['length'], field['alias'])
            field_count += 1

        if has_id_field:
            arcpy.DeleteField_management(fc, unlikely_fc_name)
        else:
            print "ok"        
            if field_count > 0:
                arcpy.DeleteField_management(fc, 'ID')
                
        
        iCur = arcpy.InsertCursor(fc)
        

        i = 0
        for feature in features:
            feat = iCur.newRow()
            attr = feature['attributes']
            for field in inFields:
                ftype = field['type']
                fval = attr[field['fname']]
                if ftype == 'DATE':
                    # Try to convert the miliseconds from epoch to a date
                    fval = datetime.date.fromtimestamp(fval / 1000).strftime("%m/%d/%Y %I:%M:%S %p")

                feat.setValue(field['tfname'], fval)


            if geomType == "POLYLINE":
                geometry = feature['geometry']
                coordList = geometry['paths']

                point = arcpy.Point()
                array = arcpy.Array()

                for f in coordList:
                    for coordPair in f:
                        point.X = coordPair[0]
                        point.Y = coordPair[1]
                        array.add(point)
                                        
                polyline = arcpy.Polyline(array, fcSR)

                array.removeAll()

                feat.shape = polyline
                
            elif geomType == "POLYGON":
                geometry = feature['geometry']
                coordList = geometry['rings']
                
                point = arcpy.Point()
                sub_array = arcpy.Array()
                array = arcpy.Array()

                j = 0

                for f in coordList:
                    k = 0
                    for coordPair in reversed(f):                        
                        k += 1
                        point.X = coordPair[0]
                        point.Y = coordPair[1]                        
                        sub_array.add(point)
                    #print str(j) + ":" + str(k - 2)
                    array.append(sub_array)
                    
                    sub_array.removeAll()
                    j += 1
                                        
                polygon = arcpy.Polygon(array, fcSR)

                '''
                # Without the fcSR the Polygon was generalized greatly
                len_arr = len(array)
                i = 0
                while i < len_arr:
                    b = array[i]
                    print len(b)
                    i += 1

                part_count = polygon.partCount
                i = 0
                while i < part_count:
                    ar = polygon.getPart(i)
                    print str(i) + ":" + str(len(ar))
                    i += 1
                '''

                array.removeAll()

                feat.shape = polygon                
            elif geomType == "POINT":
                geometry = feature['geometry']
                
                point = arcpy.Point()

                point.X = geometry['x']
                point.Y = geometry['y']

                pointGeom = arcpy.PointGeometry(point, fcSR)
                                        
                feat.shape = pointGeom
                
            elif geomType == "MULTIPOINT":

                geometry = feature['geometry']
                coordList = geometry['points']
                
                point = arcpy.Point()
                array = arcpy.Array()

                for coordPair in coordList:
                    point.X = coordPair[0]
                    point.Y = coordPair[1]
                    array.add(point)
                multiPoint = arcpy.Multipoint(array, fcSR)

                array.removeAll()

                feat.shape = multiPoint


                
            iCur.insertRow(feat)

            i += 1
            if i % 10 == 0:
                print "Feature " + str(i) + ": " + strftime(time_fmt, gmtime())

            
        

    except Exception as e:
        print e

    finally:
        print "Done"
        del iCur
    
        print "End: " + strftime(time_fmt, gmtime())

