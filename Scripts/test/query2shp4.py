import arcpy
import urllib
import json
import datetime
from time import gmtime, strftime

debug = False

def exportMapServerQueryShapefile(inQueryURL, inQueryParams, output_folder):

    '''
    Inputs:
        inQueryURL then entire path to the query
        inQueryParams represented as JSON
        output_folder where the Shapefile will be created

    Outputs:
        result dictionary
        result['ok'] = True or False
        result['message'] = Error message if faile
        restul['num_feature_inserted'] = -1 if error occurs         

    '''
    result = {}
    num_features_inserted = 0    

    iCur = arcpy.Cursor
    time_fmt = "%a, %d %b %Y %H:%M:%S"
    
    
    try:

        if debug: print "Start: " + strftime(time_fmt, gmtime())


        # Build the query_url
        '''
        # These are required by the export GPTool 
        &returnCountOnly=false
        &returnIdsOnly=false
        &returnGeometry=true
        &f=json
        '''
        
        f = json.loads(inQueryParams)
        # Force params
        f['returnCountOnly'] = 'false'
        f['returnIdsOnly'] = 'false'
        f['returnGeometry'] = 'true'
        f['f'] = 'json'
        
        params = urllib.urlencode(f)
        
        if inQueryURL[-1] != '?':
            # Add ? if not included in URL
            inQueryURL += '?'
                
        query_url = inQueryURL + params
        if debug: print query_url

        # Make the query
        furl = None
        try:
            furl = urllib.urlopen(query_url)
        except Exception as e:
            raise Exception("Could not connect to server in URL");
        return_code = furl.getcode()
        if debug: print "return code: " + str(return_code)
        if return_code != 200:
            raise Exception("Could not connect to query URL")
        resp = json.load(furl)

        try:
            displayFieldName = resp['displayFieldName']
            fieldAliases = resp['fieldAliases']
            geometryType = resp['geometryType']
            spatialReference = resp['spatialReference']
            fields = resp['fields']
            features =  resp['features']
        except:
            error = ""
            try:
                error = resp['error']['message']
            except:
                error = "No Error Message from ArcGIS Server"
            raise Exception(error)
        
        if debug: print "After JSON parsing"

        geomType = "POINT"
        if geometryType == "esriGeometryPolyline":
            geomType = "POLYLINE"
        elif geometryType == "esriGeometryPolygon":
            geomType = "POLYGON"
        elif geometryType == "esriGeometryMultipoint":
            geomType = "MULTIPOINT"
                  

        # Create Spatial Reference from the return value
        fcSR = arcpy.SpatialReference()
        fcSR.factoryCode = spatialReference['wkid']
        fcSR.create()

        # Build a field map based on the return 
        inFields = []
        tfnames = []
        for field in fields:
            if debug: print field['name'] + " : " + field['type'] + " : " + field['alias']
            fname = field['name']
            tfname = fname

            # Adjust the field name since Shapefiles only support 10 character field names
            if len(fname) > 10:
                fname8 = fname[0:8]
                for fx in "123456789abcdefghijklmnopqrstuvwxyz":
                    # Support up to 37 fields that start with same 8 characters
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
 

        # Getting ready to output
        arcpy.env.workspace = output_folder

        # Shapefile name to create
        output_shapefilename = r"output.shp"

        # If it already exists try to delete
        try:
            arcpy.Delete_management(output_shapefilename)
        except Exception as e:
            print e

        # Create Feature Class
        fc = arcpy.CreateFeatureclass_management(output_folder, output_shapefilename, geomType, '#', 'DISABLED', 'DISABLED', fcSR)

        if debug: print fc

        # Shapefile must have at least one attribue field the CreateFeatureclass method above creates a field named "ID"
        
        field_count = 0
        has_id_field = False
        unlikely_field_name = 'qetuop0987'
        for field in inFields:            
            if field['tfname'].upper() == "ID":
                # Feature Class Exporting also has a field named ID
                has_id_field = True
                if field_count == 0:
                    # Add a temp field with a name that is unlikely to collide; if no other field's have been added yet
                    arcpy.AddField_management(fc, unlikely_field_name , 'LONG', '#', '#', 0)
                # Remove the ID Field
                arcpy.DeleteField_management(fc, 'ID')

            fname = field['tfname']  
            ftype = field['type']
            flen = field['length']
            falias = field['alias']

            if ftype == "TEXT":
                if flen > 254:
                    # Max TEXT length for Shapefile is 254
                    flen = 254

            arcpy.AddField_management(fc, fname, ftype, '#', '#', flen, falias)
            field_count += 1

        if has_id_field:
            try:
                # Delete the unlikely_field_name if created
                arcpy.DeleteField_management(fc, unlikely_field_name)
            except:
                if debug: print "Couldn't delete the unlikely_field_name"
        else:
            if field_count > 0:
                try:
                    # Delete the ID field 
                    arcpy.DeleteField_management(fc, 'ID')
                except:
                    if debug: print "Couldn't delete the ID field"

        # Create a cursor to the output feature class to write features to
        iCur = arcpy.InsertCursor(fc)

        i = 0

        for feature in features:
            try:
                feat = iCur.newRow()
                attr = feature['attributes']
                for field in inFields:
                    ftype = field['type']
                    fval = attr[field['fname']]
                    if ftype == 'DATE':
                        # Try to convert the miliseconds from epoch to a date
                        fval = datetime.date.fromtimestamp(fval / 1000).strftime("%m/%d/%Y %I:%M:%S %p")
                    if ftype == 'TEXT':
                        # Truncate value to 254 characters max allowed for shapefiles
                        fval = fval[:254]

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
                num_features_inserted += 1

            except Exception as e:
                if debug: print e
            finally:
                i += 1
                if i % 10 == 0:
                    if debug: print "Feature " + str(i) + ": " + strftime(time_fmt, gmtime())

        if debug: print "Number of features added: " + str(num_features_inserted)
        
        result['num_features_inserted'] = num_features_inserted
        result['message'] = ""
        result['ok'] = True

    except Exception as e:
        if debug: print e
        # Shapefile failed to create return -1
        result['num_features_inserted'] = -1
        result['message'] = str(e)
        result['ok'] = False
    finally:
        del iCur
        if debug: print "End: " + strftime(time_fmt, gmtime())
        return result             
    



if __name__ == '__main__':

    output_folder = r"C:\Temp"



    # line
    inQueryURL = r"http://localhost:8399/arcgis/rest/services/vector/rsstest/MapServer/1/query"
    inQueryParams = '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and objectid < 100", "f": "pjson", "returnGeometry": "false"}'

    # polygon
    #inQueryURL = r"http://localhost:8399/arcgis/rest/services/vector/rsstest/MapServer/2/query"
    #inQueryParams = '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and objectid < 100", "f": "pjson"}'

    # point
    #inQueryURL = r"http://localhost:8399/arcgis/rest/services/vector/rsstest/MapServer/4/query"
    #inQueryParams = '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and objectid < 100", "f": "pjson"}'

    # multipoint
    #inQueryURL = r"http://localhost:8399/arcgis/rest/services/vector/rsstest2/MapServer/5/query"
    #inQueryParams = '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and OID < 100", "f": "pjson"}'
    

    inQueryURL = inQueryURL.strip()
    inQueryParams = inQueryParams.strip()

    
    a = exportMapServerQueryShapefile(inQueryURL, inQueryParams, output_folder)

    print a
