import arcpy
import urllib
import json

'''

Get a few features in JSON
http://localhost:8399/arcgis/rest/services/vector/rsstest/MapServer/1/query?text=&geometry=&geometryType=esriGeometryEnvelope
&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&objectIds=&where=1%3D1+and+objectid+%3C+100&time=
&returnCountOnly=false&returnIdsOnly=false&returnGeometry=true&maxAllowableOffset=&outSR=&outFields=&f=pjson

Request could be post or get.   I'm only going to support get

input will be a query URL


'''

if __name__ == '__main__':
    try:

        f = {}
        f['where'] ='1=1 and objectid < 100'
        f['returnGeometry'] = 'true'
        f['outFields'] = '*'
        f['f'] = 'pjson'
        
        params = urllib.urlencode(f)
        print params
        
        query_url = r"http://localhost:8399/arcgis/rest/services/vector/rsstest/MapServer/1/query?" + params
        print query_url

                
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
 
        output_folder = r"C:\Temp"
        output_shapefilename = r"test1.shp"

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
            arcpy.DeleteField_management(fc, 'ID')
                

        iCur = arcpy.InsertCursor(fc)
        

        for feature in features:
            feat = iCur.newRow()
            attr = feature['attributes']
            for field in inFields:
                feat.setValue(field['tfname'], attr[field['fname']])

            geometry = feature['geometry']
            coordList = geometry['paths']

            # Need to add code to handle point and polygons too
            point = arcpy.Point()
            array = arcpy.Array()

            for f in coordList:
                for coordPair in f:
                    point.X = coordPair[0]
                    point.Y = coordPair[1]
                    array.add(point)
                    
            
            polyline = arcpy.Polyline(array)

            array.removeAll()

            feat.shape = polyline

            iCur.insertRow(feat)

            
        del iCur

    except Exception as e:
        print e

    

