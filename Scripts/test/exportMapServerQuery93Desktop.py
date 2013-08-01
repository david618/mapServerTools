import arcpy, os, sys, traceback, uuid, zipfile
from arcpy import env
import urllib,json,datetime
from time import strftime, localtime
from urlparse import urlparse
import time

# Set to desktop for running from desktop
desktop = True

# The server default is 600 seconds
# Ignored when desktop = True
max_run_secs = 500

debug = True

verbose_debug = False

deployed = True

time_fmt = "%a, %d %b %Y %H:%M:%S"

shapefile_warning = '''
******* WARNING ********
Shapefiles have several limitations.
1) UTF-8 Characters are not supported in output
2) NULL values are not supported
3) Text fields longer than 254 characters
4) Fieldnames are limited to 10 characters 

Consider using File or Personal Geodatabase

******* WARNING ********
'''


def log_message(msg, level="message"):
    level = level.strip().lower()
    if level == "message":
        arcpy.AddMessage(msg)
    elif level == "warn":
        arcpy.AddWarning(msg)
    elif level == "error":
        arcpy.AddError(msg)
    print msg
        
    

def exportMapServerQueryShapefile(inQueryURL, inQueryParams, inOutputFormat, shpNullTypes, output_folder):

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
    start_time = time.time()

    iCur = arcpy.Cursor    

    fout = None

    # Upper the output Format
    outputFormat = inOutputFormat.upper()

    urlWithoutQuery = inQueryURL
    
    try:

        if debug: log_message("Start: " + strftime(time_fmt, localtime()))
        

        if inQueryURL.endswith("/query"):
            log_message("Ends with query")
            urlWithoutQuery = inQueryURL[:-len("/query")]

        elif inQueryURL.endswith("/query?"):
            log_message("Ends with query or query?")
            urlWithoutQuery = inQueryURL[:-len("/query?")]
            
        else:
            # The word query is not in the URL
            log_message("The URL should end with query; appending /query?")
            inQueryURL += "/query?"
        
        if inQueryURL[-1] != '?':
            # Add ? if not included in URL
            inQueryURL += '?'

        if urlWithoutQuery[-1] != '?':
            # Add ? if not included in URL
            urlWithoutQuery += '?'

        if outputFormat == "SHAPEFILE":
            log_message(shapefile_warning, "warn")

        if debug: log_message("OK: " + str(inQueryParams))

        if inQueryParams == "":
            inQueryParams = "{}"            
        
        # Build the query_url     
        inParams = json.loads(inQueryParams)

        f = {}
        # Set default
        f['where'] = "1=1"
        f['outFields'] = "*"
        export_all = False
        
        # Check and load Params
        for param in inParams:
            if debug: log_message("Checking param: " + str(param))
            uparam = str(param).upper()
            val = inParams[param]
            if uparam == "WHERE":                
                if val: f['where'] = str(val)
            elif uparam == "OUTFIELDS":                
                if val: f['outFields'] = str(val)
            elif uparam == "EXPORTALL":
                sval = str(val).upper()
                if sval == "TRUE":
                    export_all = True
                elif sval == "FALSE":
                    export_all = False
                else:
                    export_all = False
                    log_message("*** Invalid input for exportAll; should be True or False.  Setting to False and continuing ****", "warn")                    
            elif uparam in ["RETURNIDSONLY","RETURNCOUNTONLY","F","RETURNGEOMETRY"]:
                # The GP set these as needed
                if debug: log_message("Excluding user provided param")
            else:
                # Pass the param through as is
                f[param] = val


        objectids = []
        oid_field = ""
        query_cnt = 0
        ags10 = True

        if export_all:
            # User want to download all the features
            f['returnIdsOnly'] = 'true'
            f['returnCountOnly'] = 'false'
            f['f'] = 'json'

            params =urllib.urlencode(f)
            
            query_url = inQueryURL + params
            log_message("Get all the objectids: " + query_url)
            
            # Make the query
            furl = None
            try:
                furl = urllib.urlopen(query_url)
            except Exception as e:
                raise Exception("Could not connect to server in URL");
            return_code = furl.getcode()
            if debug: log_message("return code: " + str(return_code))
            if return_code != 200:
                raise Exception("Could not connect to query URL")
            resp = json.load(furl)

            try:
                objectids = resp['objectIds']
                query_cnt = len(objectids)
                oid_field = resp['objectIdFieldName']
                # Sort the objectids
                objectids.sort()
            except:
                # Server didn't return a objectid's
                log_message("Couldn't get the objectids. Might be a 9.3 Service")
                try:
                    # Response from 9.3 would be features
                    fieldAliases = resp['fieldAliases']
                    ags10 = False
                    log_message("This appears to be a ArcGIS 9.3 or 9.31 service.  Export All requires 10.0 or better.  Results limited by service.", "warn")
                    export_all = False
                except:
                    raise Exception("Unexpected response from service. Please check your service endpoint")
            
        else:
            # Count query
            f['returnCountOnly'] = 'true'
            f['f'] = 'json'

            params =urllib.urlencode(f)
            
            query_url = inQueryURL + params
            log_message("Get Counts Query: " + query_url)
            
            # Make the query
            furl = None
            try:
                furl = urllib.urlopen(query_url)
            except Exception as e:
                raise Exception("Could not connect to server in URL");
            return_code = furl.getcode()
            if debug: log_message("return code: " + str(return_code))
            if return_code != 200:
                raise Exception("Could not connect to query URL")
            resp = json.load(furl)

            try:
                query_cnt = resp['count']
            except:
                # Server didn't return a count
                log_message("Couldn't get the count. Might be a 9.3 Service")
                try:
                    # Response from 9.3 would be features
                    fieldAliases = resp['fieldAliases']
                    ags10 = False
                except:
                    raise Exception("Unexpected response from service. Please check your service endpoint")

        log_message("Total records matching the query: " + str(query_cnt))        


        # Force params
        f['returnCountOnly'] = 'false'
        f['returnIdsOnly'] = 'false'
        f['returnGeometry'] = 'true'
        f['f'] = 'json'
                        
        params = urllib.urlencode(f)
                        
        query_url = inQueryURL + params
        log_message("First Query: " + query_url)

        # Make the query
        furl = None
        try:
            furl = urllib.urlopen(query_url)
        except Exception as e:
            raise Exception("Could not connect to server in URL");
        return_code = furl.getcode()
        if debug: log_message("return code: " + str(return_code))
        if return_code != 200:
            raise Exception("Could not connect to query URL")
        resp = json.load(furl)

        log_message("Building Feature Class")

        try:
            error = resp['error']['message']
            # Error was returned from the server
            raise Exception(error)
        except:
            if debug: log_message("No Error Message from the server")

        try:
            geometryType = resp['geometryType']
        except:
            # The layer doesn't have GeometryType defined can't export to Shapefile
            raise Exception("Geometry Type not found in response")

        try:
            spatialReference = resp['spatialReference']
        except:
            # The layer doesn't have GeometryType defined can't export to Shapefile
            raise Exception("Spatial Reference not found in response")

        try:
            features = resp['features']
        except:
            # The layer doesn't have GeometryType defined can't export to Shapefile
            raise Exception("Features not found in response")


        # Get the fields from another call (works for 9.3,9.31,10, and 10.1
        # This can also be used to get the layer name
        f['f'] = 'json'

        params =urllib.urlencode(f)
        
        query_url = urlWithoutQuery + params
        log_message("Get Field Names and Layer Name: " + query_url)
        
        # Make the query
        furl = None
        try:
            furl = urllib.urlopen(query_url)
        except Exception as e:
            raise Exception("Could not connect to server in URL");
        return_code = furl.getcode()
        if debug: log_message("return code: " + str(return_code))
        if return_code != 200:
            raise Exception("Could not connect to query URL")
        resp = json.load(furl)            
        
        try:
            fields = resp['fields']
        except:
            # The layer doesn't have GeometryType defined can't export to Shapefile
            raise Exception("Fields not found in response")

        layerid= ""
        try:
            layerid = str(resp['id'])
        except:
            raise Exception("Could not determine the layer id!")

        layername = ""                    
        try:
            layername = resp['name']
        except:
            # Let this default to output + layerid 
            layername = "output" + layerid

                            
        if debug: log_message("After JSON parsing")

        geomType = "POINT"
        if geometryType == "esriGeometryPolyline":
            geomType = "POLYLINE"
        elif geometryType == "esriGeometryPolygon":
            geomType = "POLYGON"
        elif geometryType == "esriGeometryMultipoint":
            geomType = "MULTIPOINT"
                  

        # Create Spatial Reference from the return value
        fcSR = arcpy.SpatialReference()
        try:
            fcSR.factoryCode = spatialReference['wkid']
            fcSR.create()
        except:
            if debug: log_message("Spatial reference has no wkid")
            try:
                wkt = spatialReference['wkt']
                fcSR.loadFromString(wkt)
            except:
                if debug: log_message("Spatial reference has no wkt")
                raise Exception("Could not set the Spatial Reference")

        # Build a field map based on the return 
        inFields = []
        tfnames = []

        if debug: log_message("Read the fields")
        for field in fields:
            if debug: log_message(field)
            if debug: log_message(field['name'] + " : " + field['type'] + " : " + field['alias'])
            fname = field['name']
            tfname = fname

            if outputFormat == "SHAPEFILE":
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

            # Replace Special Characters (These are not allowed in Personal or File Geodatabase)
            reps = [".","!","`",'"',"[","]","(",")"]
            for rep in reps:
                tfname = tfname.replace(rep,"_")    
            
            if outputFormat == "SHAPEFILE":
                # Shapefiles can't have any special characters (I may have missed some here)
                reps = ["@","~","#",'$',"%","&","*","-","+","=",","]
                tfname = tfname.replace(rep,"_")    
            

            TFNAMEU = tfname.upper()
            reservedFieldNames = ["SHAPE_LENGTH","SHAPE_AREA","SHAPE.AREA","SHAPE.LEN","ST_AREA(SHAPE)","ST_LENGTH(SHAPE)"]
            if TFNAMEU in reservedFieldNames:
                # Reserved Field Name
                log_message("Reserved Field Name: " + tfname)
                continue
    
            tfnames.append(tfname)

                        
            if field['type'] == 'esriFieldTypeString':
                if ags10:
                    flen = field['length']
                else:
                    flen = 254
                inFields.append({'fname': fname, 'tfname': tfname, 'length': flen, 'type':'TEXT', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeDouble':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'DOUBLE', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeDate':
                if ags10:
                    flen = field['length']
                else:
                    flen = 8                
                inFields.append({'fname': fname, 'tfname': tfname, 'length': field['length'], 'type':'DATE', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeSmallInteger':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'SHORT', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeInteger':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'LONG', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeFloat':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'FLOAT', 'alias':field['alias']})            

        fc = None

        try:
            arcpy.Delete_management(r'in_memory\temp')
        except:
            if debug: "Failed delete in_memory\temp.  Probably because it doesn't exist"
        
        fc = arcpy.CreateFeatureclass_management(r'in_memory', "temp", geomType, '#', 'DISABLED', 'DISABLED', fcSR)

        '''
        if outputFormat == "SHAPEFILE":
            # Getting ready to output
            arcpy.env.workspace = output_folder

            # Shapefile name to create
            output_shapefilename = r"output.shp"

            # Create Feature Class
            fc = arcpy.CreateFeatureclass_management(output_folder, output_shapefilename, geomType, '#', 'DISABLED', 'DISABLED', fcSR)
        elif outputFormat == "FILEGEODATABASE":
            # Create File Geodatabase
            try: 
                db = arcpy.CreateFileGDB_management(output_folder, "export", "9.3")
                fc = arcpy.CreateFeatureclass_management(db, "output", geomType, '#', 'DISABLED', 'DISABLED', fcSR)                
            except:
                raise Exception("Could not create File Geodatabase")                        

        elif outputFormat == "PERSONALGEODATABASE":
            # Create Personal Geodatabase
            try: 
                db = arcpy.CreatePersonalGDB_management(output_folder, "export", "9.3")
                fc = arcpy.CreateFeatureclass_management(db, "output", geomType, '#', 'DISABLED', 'DISABLED', fcSR)                
            except:
                raise Exception("Could not create Personal Geodatabase")                                    
        else:
            raise Exception("Exception unsupported output format")
        '''

        if debug: log_message("fc: " + str(fc))

        # Shapefile must have at least one attribue field the CreateFeatureclass method above creates a field named "ID"
        
        field_count = 0
        has_id_field = False

        if outputFormat == "SHAPEFILE":
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
                    # Max text length is 254 for Shapefile
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
                    if debug: log_message("Couldn't delete the unlikely_field_name")
            else:
                if field_count > 0:
                    try:
                        # Delete the ID field 
                        arcpy.DeleteField_management(fc, 'ID')
                    except:
                        if debug: log_message("Couldn't delete the ID field")
        else:
            # File or Personal Geodatabase much easier
            for field in inFields:            
                fname = field['tfname']  
                ftype = field['type']
                flen = field['length']
                falias = field['alias']

                arcpy.AddField_management(fc, fname, ftype, '#', '#', flen, falias)
                field_count += 1


        log_message("Feature Class Created")
            

        # Create a cursor to the output feature class to write features to
        iCur = arcpy.InsertCursor(fc)


        # Create a log file for outputing any features rejected
        fout = open(os.path.join(output_folder,"log.txt"), "w")        

        if outputFormat == "SHAPEFILE":
            fout.write(shapefile_warning)

        max_features_returned = len(features)

        if export_all:
            log_message("Begin Exporting All")
            fout.write("**** Begin Exporting All ****\n")
            if len(objectids) == 0:
                raise Exception("Service returned no features")

            if len(objectids) == 0:
                raise Exception("Service returned no features")

            more_ids = True

            i = 0

            everything = False
            #"".join(f['where'].split())  This will strip out all white space
            # f['where'].replace(" ","")  This takes out just spaces
            if f['where'].replace(" ","") == "1=1":
                everything = True

            if debug: log_message("EVERYTHING: " + str(everything))
            if debug: log_message("where: " + f['where'])

            features_processed = 0
            
            while more_ids:
                
                last_index = 0
                min_objectid = objectids[i]
                try:
                    max_objectid = objectids[i + max_features_returned]
                    lastindex = i + max_features_returned
                except IndexError:
                    # past last set to last value
                    max_objectid = objectids[-1] + 1
                    lastindex = len(objectids)
                    more_ids = False

                features_processed += (lastindex - i)
                if debug: log_message("features_processed = " + str(features_processed))
                # join is much more consise
                oids = "(" + ",".join(map(str,objectids)) + ")"                
                '''
                oids = "("
                j = i
                while j < lastindex:
                    oids += str(objectids[j]) + ","
                    j +=1
                oids = oids[:-1] + ")"
                '''
                if verbose_debug: log_message("oids: " + oids)

                where = ""
                if everything:
                    where = oid_field + ">=" + str(min_objectid) + " and " + oid_field + "<" + str(max_objectid)
                else:
                    where = oid_field + " in " + oids

                f['where'] = where
                f['returnCountOnly'] = 'false'
                f['returnIdsOnly'] = 'false'
                f['returnGeometry'] = 'true'
                f['f'] = 'json'   

                params = urllib.urlencode(f)
                                
                query_url = inQueryURL + params
                log_message("Data Query: " + query_url)
                percent_complete = "%.2f" % (float(features_processed)/float(query_cnt)*100.0)
                log_message("Percent complete: " + percent_complete)

                # Make the query
                furl = None
                try:
                    if everything:
                        # If everything use a get it's shorter
                        furl = urllib.urlopen(query_url)
                    else:
                        # Use POST if request is OID in (list of OIDS); Get won't support such a long input
                        furl = urllib.urlopen(inQueryURL, params)
                except Exception as e:
                    raise Exception("Could not connect to server in URL");
                return_code = furl.getcode()
                if debug: log_message("return code: " + str(return_code))
                if return_code != 200:
                    raise Exception("Could not connect to query URL")
                resp = json.load(furl)

                try:
                    features = resp['features']
                except:
                    # The layer doesn't have GeometryType defined can't export to Shapefile
                    raise Exception("Features not found in response")

                num_features_inserted += exportFeatures(iCur, features, inFields, geomType, fcSR, outputFormat, shpNullTypes, fout)
            
                if (time.time() - start_time) > max_run_secs and not desktop:
                    # Idea is to stop before the SOC times out and send the user what I was able to extract
                    log_message("************************************************", "warn")
                    log_message("Times up.  For full export you might need to run the desktop version.", "warn")
                    log_message("************************************************", "warn")
                    break
                i = i + max_features_returned


                            
            fout.write("**** End Exporting All ****\n")
            log_message("End Exporing All")
        else:
            log_message("Begin Exporting")
            # Only exporting what the map service returns in a single web call
            if len(features) < query_cnt:
                log_message("************************************************", "warn")
                log_message("Map Service only returned " + str(max_features_returned) + " of " + str(query_cnt) + " features matching your query.", "warn")
                log_message("************************************************", "warn")

                fout.write("Map Service only returned " + str(max_features_returned) + " of " + str(query_cnt) + " features matching your query.\n")
            fout.write("**** Features rejected ****\n")
            num_features_inserted = exportFeatures(iCur, features, inFields, geomType, fcSR, outputFormat, shpNullTypes, fout)            
            fout.write("**** End Features rejected ****\n")
            log_message("Export Complete")

        if ags10:
            fout.write("Number of features added: " + str(num_features_inserted) + " of " + str(query_cnt))
            if debug: log_message("Number of features added: " + str(num_features_inserted) + " of " + str(query_cnt))
        else:
            fout.write("Number of features added: " + str(num_features_inserted))
            if debug: log_message("Number of features added: " + str(num_features_inserted))


        output_fcname = layername
        
        reps = [".","!","`",'"',"[","]","(",")","@","~","#",'$',"%","&","*","-","+","=",",","/","\\"]
        for rep in reps:
            output_fcname = output_fcname.replace(rep,"_")    
                
        if debug: log_message("Output FC Name: " + output_fcname)
        
        # Copy from memory to disk
        if outputFormat == "SHAPEFILE":
            # Getting ready to output
            arcpy.env.workspace = output_folder

            # Shapefile name to create
            #output_shapefilename = r"output.shp"
            output_shapefilename = output_fcname + ".shp"

            # Create Feature Class
            fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\temp', output_folder, output_shapefilename)
        elif outputFormat == "FILEGEODATABASE":
            # Create File Geodatabase
            try: 
                db = arcpy.CreateFileGDB_management(output_folder, "export", "9.3")
                fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\temp', db, output_fcname)
            except:
                raise Exception("Could not create File Geodatabase")                        

        elif outputFormat == "PERSONALGEODATABASE":
            # Create Personal Geodatabase
            try: 
                db = arcpy.CreatePersonalGDB_management(output_folder, "export", "9.3")
                fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\temp', db, output_fcname)                              
            except:
                raise Exception("Could not create Personal Geodatabase")                                    
        else:
            raise Exception("Exception unsupported output format")


        
        result['num_features_inserted'] = num_features_inserted
        result['message'] = ""
        result['ok'] = True
        result['fc'] = fc


    except Exception as e:
        if debug: log_message("ERROR: " + str(e))
        # Shapefile failed to create return -1
        result['num_features_inserted'] = -1
        result['message'] = str(e)
        result['ok'] = False
        result['fc'] = None

    finally:
        if iCur:
            del iCur
            
        try:
            # For some reason del iCur leaves locks
            # The Following line fails; however, it remove the locks
            # These locks will prevent the service from working with "Local Jobs Directory"
            arcpy.CreateFileGDB_management("in_memory","whatever","9.3")
        except:
            log_message("OK: Clearing the locks")            
        if debug: log_message("End: " + strftime(time_fmt, localtime()))
        try:
            fout.close()
        except:
            if debug: log_message("fout failed to close.")
        
        return result             
    

def exportFeatures(iCur, features, inFields, geomType, fcSR, outputFormat, shpNullTypes, fout):
    i = 0  # This is counting total number of features attempted to load
    num_features_inserted = 0
    for feature in features:        
        feat = None
        try:
            feat = iCur.newRow()
            attr = feature['attributes']
            for field in inFields:
                ftype = field['type']
                fval = attr[field['fname']]

                if fval is None and outputFormat == "SHAPEFILE":
                    # Set null values for Shapefile Export
                    if ftype == 'DATE':
                        fval = shpNullTypes['date']
                    elif ftype == 'TEXT':
                        fval = shpNullTypes['text']
                    elif ftype == "DOUBLE":
                        fval = shpNullTypes['double']
                    elif ftype == "SHORT":
                        fval = shpNullTypes['short']
                    elif ftype == "LONG":
                        fval = shpNullTypes['long']
                    elif fval == "FLOAT":
                        fval = shpNullTypes['float']
                 
                if ftype == 'DATE':
                    if fval:                                
                        # Try to convert the miliseconds from epoch to a date if not null
                        fval = datetime.date.fromtimestamp(fval / 1000).strftime("%m/%d/%Y %I:%M:%S %p")
                if ftype == 'TEXT' and outputFormat == "SHAPEFILE":
                    if fval:
                        # Truncate value to 254 characters max allowed for shapefiles if not null
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
            if debug: log_message("Feature Failed to Export: " + str(e))
            fout.write(str(feature))
        finally:
            if feat:
                del feat
            i += 1
            if i % 10 == 0:
                if verbose_debug: log_message("Feature " + str(i) + ": " + strftime(time_fmt, localtime()))
    return num_features_inserted
            

def zipfolder(folder, zipFile):
    '''
    This function fips all the files in a folder
    It will go one folder deep and add those to the zip
    ".lock" files are excluded
    '''

    num_files_added = 0
    try:
        if not os.path.isdir(folder):
            raise Exception("zipfolder input must be a folder")

        if debug: log_message("Zipping folder: " + folder)



        for item in os.listdir(folder):
            fullname = os.path.join(folder,item)
            if debug: log_message("Item: " + fullname)
            if os.path.isdir(fullname):
                # subdir
                for item2 in os.listdir(fullname):
                    if os.path.isdir(item2):
                        # subdir in subdir (ignore)
                        if debug: log_message("Skipping sub-subdir")
                    else:
                        # file in subdir
                        if not item2.endswith('.lock') and not item2.endswith(".ldb"):
                            # ignore lock files
                            try:
                                zipFile.write(os.path.join(fullname,item2), \
                                           os.path.join(os.path.basename(fullname),item2))
                                num_files_added += 1
                            except IOError:
                                if debug: log_message("Failed to add file to zip")
            else:
                # file
                if not item.endswith('.lock') and not item.endswith(".ldb"):
                    # ignore lock files
                    try:
                        zipFile.write(fullname, item)
                        num_files_added += 1
                    except IOError:
                        if debug: log_message("Failed to add file to zip")
    except Exception as e:
        if debug: log_message("Zip failed: " + str(e))
    finally:
        return num_files_added



if __name__ == '__main__':

    try:
        valid_servers = []
        valid_servers.append(r"http://localhost:8399")
        valid_servers.append(r"http://12.187.20.60")
        valid_servers.append(r"http://ags10a")
        check_valid_servers = False

        # Main Function this is where things start   (Get  parameters from the GP)
        inQueryURL = arcpy.GetParameterAsText(0).strip() # Query URL
        inQueryParams = arcpy.GetParameterAsText(1).strip() # Query Parametrs as JSON 
        inOutputFormat = arcpy.GetParameterAsText(2).strip() # Format (Shapefile, FileGeodatabase, PersonalGeodatabase)
        inShapefileNulls = arcpy.GetParameterAsText(3).strip()  # JSON String 
        # If you add a parameter make sure to update the output index at end of script

        shapefileNulls = {}
        shapefileNulls['date'] = 0
        shapefileNulls['text'] = ""
        shapefileNulls['double'] = 0.0
        shapefileNulls['float'] = 0.0
        shapefileNulls['long'] = 0
        shapefileNulls['short'] = 0
        
        if inShapefileNulls != "":
            try:
                if debug: log_message(inShapefileNulls)
                # Parse the inShapefileNulls should be a json string {"int":value,"text":value, ...}
                shpnulls = json.loads(inShapefileNulls)
                if debug: log_message(shpnulls)                

                for a in shpnulls:
                    try: 
                        if a == "date" or a == "short" or a == "long":                        
                            shapefileNulls[a] = int(shpnulls[a])
                        elif a == "text":
                            shapefileNulls[a] = str(shpnulls[a])
                        elif a == "double" or a == "float":
                            shapefileNulls[a] = float(shpnulls[a])
                        else:
                            log_message("***************** Unrecognized key for Null Types *****************","warn")
                    except:
                        raise Exception("Invalid Null value for " + a, "warn")
                    
                
            except Exception as e:
                log_message(str(e))                
                raise Exception("Invalid ShapefileNulls parameter")
        
        if debug: log_message("shapefileNulls: " + str(shapefileNulls))



        #  TESTING 

        # line
        #inQueryURL = r"http://localhost:8399/arcgis/rest/services/vector/rsstest/MapServer/1/query"
        #inQueryParams = '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and objectid < 100", "f": "pjson", "returnGeometry": "false"}'

        # polygon
        #inQueryURL = r"http://localhost:8399/arcgis/rest/services/vector/rsstest/MapServer/2/query"
        #inQueryParams = '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and objectid < 100", "f": "pjson"}'

        # point
        #inQueryURL = r"http://localhost:8399/arcgis/rest/services/vector/rsstest/MapServer/4/query"
        #inQueryParams = '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and objectid < 100", "f": "pjson"}'

        # multipoint
        #inQueryURL = r"http://localhost:8399/arcgis/rest/services/vector/rsstest2/MapServer/5/query"
        #inQueryParams = '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and OID < 100", "f": "pjson"}'

        # multipoint
        #inQueryURL = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/NTAD2011/MapServer/0/query"
        #inQueryParams = '{"outFields": "*", "where": "ALL", "f": "pjson"}'
        #inOutputFormat = "Shapefile"

        # 9.3 Server Service
        #http://maps.mygrcity.us/ArcGIS/rest/services/California/MapServer/0

        #  TESTING 

        '''
        Example inQueryParams:
        '{"returnGeometry": "true", "outFields": "*", "where": "1=1 and objectid < 100", "f": "pjson"}'

        The following params are set by the tool.  They override any values specified in inQueryParams
        &returnCountOnly=false
        &returnIdsOnly=false
        &returnGeometry=true
        &f=json
        '''

        # Strip off any params stuck onto the URL
        a = urlparse(inQueryURL)

        server = a.scheme + "://" + a.netloc
        if debug: log_message("Server: " + server)

        url_withoutParams = server + a.path        

        if check_valid_servers:    
            if not server in valid_servers:
                raise Exception("Unsupported server.  The following servers are supported: " + str(valid_servers))

        if deployed and not desktop:
            # Use this when deployed as GP Service
            scratchPath = env.scratchWorkspace            
        else:
            # Use this when testing from Desktop
            scriptPath = sys.path[0]
            toolSharePath = os.path.dirname(scriptPath)
            scratchPath = os.path.join(toolSharePath, "Scratch")
            if not os.path.exists(scratchPath):
                # Create Scratch folder if needed
                os.mkdir(scratchPath)
                
        if debug: log_message("scratchPath: " + scratchPath)

        # Create a random output folder
        rndFolderName = str(uuid.uuid4());
        
        outFolder = os.path.join(scratchPath, rndFolderName)

        os.mkdir(outFolder)

        if debug: log_message("outFolder: " + outFolder)
        
        a = exportMapServerQueryShapefile(url_withoutParams, inQueryParams, inOutputFormat, shapefileNulls, outFolder)

        if debug: log_message("a: " + str(a))

        if not a['ok']:
            raise Exception(a['message'])

        if a['num_features_inserted'] <= 0:
            raise Exception("No features exported")

        if desktop:
            # Don't zip and retun the fc
            arcpy.SetParameterAsText(4, a['fc'])            
        else:
            log_message("Creating zip file")
            # Name of the outfile 
            outfile = os.path.join(scratchPath, "export.zip")

            if debug: log_message("outfile: " + outfile)

            # Create the zip file
            zipFile = zipfile.ZipFile(outfile, 'w', zipfile.ZIP_DEFLATED)
            num_files_added = zipfolder(outFolder, zipFile)
            zipFile.close()

            if num_files_added == 0:
                log_message("Export Failed!", "error")
                outfile = None

            # Send the zip file back to the user
            arcpy.SetParameterAsText(4, outfile)

    except:
        # Return any python specific errors as well as any errors from the geoprocessor
        #

        
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n    " + \
                str(sys.exc_type)+ ": " + str(sys.exc_value) + "\n"


        msgs = "GP ERRORS:\n" + arcpy.GetMessages(2) + "\n"

        if debug:
            log_message(pymsg, "error")
        else:
            log_message(str(sys.exc_value), "error")

        if verbose_debug:
            log_message(msgs, "error")

