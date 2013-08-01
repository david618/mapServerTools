import arcpy, os, sys, traceback, uuid, zipfile
from arcpy import env
import urllib,urllib2,json,datetime
from time import strftime, localtime
from urlparse import urlparse
import time
import codecs
import math

# The server default is 600 seconds
# Ignored when desktop = True
max_run_secs = 540

debug = True

verbose_debug = False

time_fmt = "%a, %d %b %Y %H:%M:%S"

TIMEOUTSECS = 20

shapefile_warning = '''
******* WARNING ********
Shapefiles and dBASE have several limitations.
1) UTF-8 Characters are not supported in output
2) NULL values are not supported
3) Text fields longer than 254 characters
4) Fieldnames are limited to 10 characters 

Consider using File or Personal Geodatabase

******* WARNING ********
'''

# These decode functions were added to support json returning string types instead of unicode
# The unicode types were causing issues when turning them into URL Params
# Reference: http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-unicode-ones-from-json-in-python

def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
           key = key.encode('utf-8')
        if isinstance(value, unicode):
           value = value.encode('utf-8')
        elif isinstance(value, list):
           value = _decode_list(value)
        elif isinstance(value, dict):
           value = _decode_dict(value)
        rv[key] = value
    return rv

# log_message function was a convient way for me to output messages to the screen

def log_message(msg, level="message"):
    level = level.strip().lower()
    if level == "message":
        arcpy.AddMessage(msg)
    elif level == "warn":
        arcpy.AddWarning(msg)
    elif level == "error":
        arcpy.AddError(msg)
    print msg


def exportMapServerLayer(inQueryURL, inQueryParams, inOutputFormat, shpNullTypes, \
                         output_folder, output_workspace, desktop, authheader, clip=False):

    '''
    Inputs:
        inQueryURL: URL to Query 
        inQueryParams:  Query Parameters as JSON
        inOutputFormat: Desired output Format
        shpNullTypes: What values to use for Nulls in Shapefile
        output_folder: Where to create the output        
        output_workspace: where the featureclass will be added
        desktop: Set to True for desktop version or false for service
        authheader: Set if the service requires HTTP Basic Authentication

    Outputs:
        result dictionary
        result['ok'] = True or False
        result['message'] = Error message if faile
        result['num_feature_inserted'] = -1 if error occurs
        result['fc'] = Feature Class 

    '''
    result = {}
    num_features_inserted = 0
    start_time = time.time()

    iCur = arcpy.Cursor    

    fout = None
    ftabdelimited = None

    # Upper the output Format
    outputFormat = inOutputFormat.upper()

    urlWithoutQuery = inQueryURL
    
    try:        
        if debug: log_message("Start: " + strftime(time_fmt, localtime()))
    
        # *******************************************************    
        # The code was designed to accept the URL with query 
        # *******************************************************    
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

        # *******************************************************
        # Get the field names and layer name (works for 9.3,9.31,10, and 10.1
        # *******************************************************    
        f = {}

        f['f'] = 'json'

        params =urllib.urlencode(f)

        req = urllib2.Request(urlWithoutQuery, params)

        if authheader != "":
            req.add_header("Authorization", authheader) 
        
        query_url = urlWithoutQuery + params
        log_message("Get Field Names and Layer Name: " + query_url)
        
        # Make the query
        furl = None
        try:
            furl = urllib2.urlopen(req)
        except Exception as e:
            raise Exception("Could not connect to server in URL");
        return_code = furl.getcode()
        if debug: log_message("return code: " + str(return_code))
        if return_code != 200:
            raise Exception("Could not connect to query URL")
        resp = json.load(furl)            

        # Check for Error from Server
        try:
            error = resp['error']['message']
            raise ValueError(str(resp))
        except ValueError:
            raise Exception(str(resp))
        except Exception:
            if debug: log_message("No Error Message from the server")

        # Determine if server is version 10.0 or newer
        ags10 = True
        try:
            version = resp['currentVersion']
        except:
            # 9.3x doesn't have a currentVersion Parameter
            ags10 = False

        # Determine the default Spatial Reference (based on extent)
        SR = None
        try:
            SR = resp['extent']['spatialReference']        
        except:
            log_message("extent/spatialReference not found in service", "warn")

        defaultSR = None
        if not SR is None:
            # Create spatial ref from service response        
            defaultSR = arcpy.SpatialReference()
            try:
                defaultSR.factoryCode = SR['wkid']
                defaultSR.create()
            except:
                if debug: log_message("Default Spatial reference has no wkid")
                try:
                    defaultwkt = SR['wkt']
                    defaultSR.loadFromString(defaultwkt)
                except:
                    if debug: log_message("Default Spatial reference has no wkt")
                    raise Exception("Could not set the Default Spatial Reference")

         # Get Layer Type (Feature Layer, Table, etc)
        layertype = ""  
        try:
            layertype = resp['type']
        except:
            # The layer doesn't have GeometryType defined can't export to Shapefile
            raise Exception("Could not determine layer type from response")
        
        if not layertype in ["Feature Layer","Table"]:
            raise Exception("Cannot export type: " + str(layertype))

        # Get the fields
        try:
            fields = resp['fields']
        except:
            # The layer doesn't have GeometryType defined can't export to Shapefile
            raise Exception("Fields not found in response")

        # Get the layerid
        layerid= ""
        try:
            layerid = str(resp['id'])
        except:
            raise Exception("Could not determine the layer id!")

        # Get the layername
        layername = ""                    
        try:
            layername = resp['name']
        except:
            # Let this default to output + layerid 
            layername = "output" + layerid

        # *******************************************************    
        # Create the output feature class name 
        # *******************************************************    
        #output_fcname = layername
        output_fcname = arcpy.ValidateTableName(layername, output_workspace)
        if debug: log_message("output_fcname: " + str(output_fcname))
        num = 0
        while arcpy.Exists(str(output_workspace) + "\\" + output_fcname):
            num += 1
            output_fcname = output_fcname + str(num)
            if num > 999:
                raise Exception("Couldn't fine a unique feature class name!")
                    
        '''
        # Remove any invalid characters
        reps = [":"," ",".","!","`",'"',"[","]","(",")","@","~","#",'$',"%","&","*","-","+","=",",","/","\\"]
        for rep in reps:
            output_fcname = output_fcname.replace(rep,"_")   
        
        # if the layername starts with a digit prefix with "a"
        try:
            if verbose_debug: log_message("First Character is: " + str(output_fcname[0]))
            int(output_fcname[0])
            output_fcname = "a" + output_fcname
        except:
            # First character is a number; not allowed prefix with the letter a
            if verbose_debug: log_message("fcname doesn't start with a number")
        '''
        
        # If output type is SHAPEFILE warn the user of potential impacts
        if outputFormat == "SHAPEFILE" or outputFormat == "DBASEFILE":
            log_message(shapefile_warning, "warn")

        # Process inQueryParams
        if debug: log_message("inQueryParams: " + str(inQueryParams))

        if inQueryParams == "":
            inQueryParams = "{}"            
        
        # Build the query_url
        try:
            inParams = json.loads(inQueryParams, object_hook=_decode_dict)            
        except Exception as e:
            raise Exception("Invalid inQueryParams. " + str(e))

        if debug: log_message("inParams: " + str(inParams))
        
        # *******************************************************    
        # Parse inQueryParams
        # *******************************************************            
        # defaults
        f['where'] = "1=1" 
        f['outFields'] = "*" 
        export_all = False
        inSR = defaultSR
        inGeometryType = "esriGeometryEnvelope"
        inGeometry = None
        
        # Check and load Params
        for param in inParams:
            if debug: log_message("Checking param: " + str(param))
            # upper to make param checks case insensitive
            uparam = str(param).upper()
            val = inParams[param]
            if uparam == "WHERE":                
                if val: f['where'] = str(val)
            elif uparam == "OUTFIELDS":                
                if val: f['outFields'] = str(val)
            elif uparam == "INSR":
                # User specified input spatial reference
                SR = val
                try:
                    # User may have specified just a WKID number                    
                    wkid = int(SR)
                    inSR = arcpy.SpatialReference()
                    inSR.factoryCode = wkid
                    inSR.create()                    
                except ValueError:
                    # Perhaps user specified Spatial Reference as JSON
                    inSR = arcpy.SpatialReference()
                    SR = SR.replace("\\\\","\\")
                    SR = json.loads(SR, object_hook=_decode_dict)

                    try:
                        inSR.factoryCode = SR['wkid']
                        inSR.create()
                    except KeyError:
                        if debug: log_message("Input Spatial reference has no wkid")
                        try:
                            inwkt = SR['wkt']
                            inSR.loadFromString(inwkt)
                        except:
                            if debug: log_message("Input Spatial reference has no wkt")
                            raise Exception("Could not set the Input Spatial Reference")
                except:
                    raise Exception("Failed to create input Spatial Reference")
                
                f[param] = val
            elif uparam == "GEOMETRYTYPE":
                inGeometryType = val
                f[param] = val
            elif uparam == "GEOMETRY":
                inGeometry = val
                f[param] = val                
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
                # The GP Tool sets these as needed; discard user provided inputs
                if debug: log_message("Excluding user provided param")
            else:
                # Pass the other param through as is
                f[param] = val

        if not ags10 and export_all:
            # exportAll not supported 
            log_message("Export All not supported for ArcGIS Server 9.3 or 9.3.1.  I'll export what I can.")
            export_all = False

        if debug: log_message("f: " + str(f))


        # *******************************************************    
        # Create clipPoly if user request clip
        # *******************************************************            

        clipPoly = None
        
        if clip:
            if debug: log_message("Clip: " + str(clip))
            if debug: log_message("inGeometry: " + str(inGeometry))

            if inGeometry is None:
                if debug: log_message("You must specify a polygon or envelope geometry to clip", "warn")
                clip = False
            else:
            
                try:
                    point = arcpy.Point()
                    sub_array = arcpy.Array()
                    array = arcpy.Array()
                                    
                    if inGeometryType == "esriGeometryPolygon":

                        inGeom = json.loads(inGeometry , object_hook=_decode_dict)
                        coordList = inGeom['rings']

                        j = 0

                        for coord in coordList:
                            k = 0
                            for coordPair in reversed(coord):                        
                                k += 1
                                point.X = coordPair[0]
                                point.Y = coordPair[1]                        
                                sub_array.add(point)
                            #print str(j) + ":" + str(k - 2)
                            array.append(sub_array)
                            
                            sub_array.removeAll()
                            j += 1

                        if inSR is None:
                            clipPoly = arcpy.Polygon(array)
                        else:                        
                            clipPoly = arcpy.Polygon(array, inSR)                        
                    elif inGeometryType == "esriGeometryEnvelope":

                        coords = inGeometry.split(",")
                        point.X = coords[0]
                        point.Y = coords[1]
                        array.add(point)
                        point.X = coords[0]
                        point.Y = coords[3]
                        array.add(point)
                        point.X = coords[2]
                        point.Y = coords[3]
                        array.add(point)
                        point.X = coords[2]
                        point.Y = coords[1]
                        array.add(point)
                        point.X = coords[0]
                        point.Y = coords[1]
                        array.add(point)
                        if inSR is None:
                            clipPoly = arcpy.Polygon(array)
                        else:                        
                            clipPoly = arcpy.Polygon(array, inSR)                                                            
                        
                    else:
                        # Clip not supportted
                        log_message("You can only clip with Envelope or Polygon.", "warn");
                        clip = False
                except Exception as e:
                    raise Exception("Couldn't parse the geometry specified in inQueryParams");                



        # *******************************************************    
        # Process and create Fields for output
        # *******************************************************            

        # Fields requested
        outFields = f['outFields']
        oFields = outFields.split(",")

        # Build a field map based on the return 
        inFields = []
        tfnames = []

            
        if outFields.strip() != "*":
            # Not * => User provided a list of fields 
            fnames = []
            # Create a list of field names (fnames) returne from the services (fields)
            for field in fields:
                fnames.append(field['name'])

            fields_not_found = []
            # Go through each field the user asked for
            for rField in oFields:                
                if not rField in fnames:
                    # if a field asked for is not found append to list
                    fields_not_found.append(rField)

            # Abort export the query will fail if the user specifies an invalid fieldname
            if len(fields_not_found) > 0:
                raise Exception ("Field(s) not found: " + str(fields_not_found), "warn")
        
        
        if debug: log_message("Read the fields")
        for field in fields:
            # Go through each field
            fname = None
            ftype = None
            falias = ""
            flen = None

            try:
                fname = field['name']
            except:
                raise Excpetion("Unable to read field name")
        
            try:
                ftype = field['type']
            except:
                raise Excpetion("Unable to read field type")

            try:
                falias = field['alias']
            except:
                falias = fname

            try:
                flen = field['length']
            except:
                if ftype == "esriFieldTypeString":
                    # Default to largest allowed value output Format
                    if outputFormat in ["SHAPEFILE", "DBASEFILE"]:
                        flen = 254
                    else:                    
                        flen = 2147483647
                elif ftype == "esriFieldTypeDate":
                    flen = 8
                                
            tfname = fname

            addField = False
            if outFields.strip() == "*":
                # The * means add them all
                addField = True
            else:
                if fname in oFields:
                    addField = True                                

            if not addField:
                # User did not request this field
                continue

            if verbose_debug:
                log_message(field)
                log_message(fname + " : " + ftype + " : " + falias + " : " + str(flen))
                log_message("outputFormat: " + outputFormat)


            '''
            # Attempt to use ValidFieldName instead of this; Resulted in issues with Shape.len and HYPERLINK_
            tfname = arcpy.ValidateFieldName(fname,output_workspace)

            num = 0
            while num < 99:
                try:
                    tfnames.index(tfname)
                    
                except ValueError as e:
                    # Value not found ok to append
                    break;
                
                num += 1
                if num < 10:
                    tfname = tfname[:-1] + str(num)
                else:
                    tfname = tfname[:-2] + str(num)

            if num == 99:
                raise Exception("To many fields that start with: " + tfname[:-2])
            '''
                
            
            
            if outputFormat != "TABDELIMITEDFILE":                
                # Replace Special Characters (These are not allowed in anything except TABDELIMITEDFILE)
                reps = [".","!","`",'"',"[","]","(",")"]
                for rep in reps:
                    tfname = tfname.replace(rep,"_")    
            
            if outputFormat == "SHAPEFILE" or outputFormat == "DBASEFILE":
                # Shapefiles can't have any special characters (I may have missed some here)
                reps = ["@","~","#",'$',"%","&","*","-","+","=",","]
                tfname = tfname.replace(rep,"_")   

            if outputFormat == "SHAPEFILE" or outputFormat == "DBASEFILE":
                # Adjust the field name since Shapefiles only support 10 character field names
                if len(tfname) > 10:
                    fname8 = tfname[0:8]
                    for fx in "123456789abcdefghijklmnopqrstuvwxyz":
                        # This substituion support up to 35 fields that start with same 8 characters
                        tfname = fname8 + "_" + fx
                        try:
                            tfnames.index(tfname)
                        except ValueError as e:
                            # Value not found ok to append
                            break;
                        if fx == "z":
                            raise Exception("More than 35 fields start with the same 8 characters!")
                                   
            if outputFormat in ["SHAPEFILE","PERSONALGEODATABASE","FILEGEODATABASE"]:
                # Rerserved field names for feature classes
                TFNAMEU = tfname.upper()
                if debug: log_message("TFNAMEU:" + TFNAMEU)
                reservedFieldNames = ["SHAPE_LENGTH","SHAPE_AREA","SHAPE_LEN","ST_AREA_SHAPE_","ST_LENGTH_SHAPE_"]
                if TFNAMEU in reservedFieldNames:
                    # Reserved Field Name
                    log_message("Leaving out Reserved Field Name: " + tfname)
                    continue
            
            tfnames.append(tfname)
                        
            if ftype == 'esriFieldTypeString':                                
                inFields.append({'fname': fname, 'tfname': tfname, 'length': flen, 'type':'TEXT', 'alias':falias})
            elif ftype == 'esriFieldTypeDouble':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'DOUBLE', 'alias':falias})
            elif ftype == 'esriFieldTypeDate':             
                inFields.append({'fname': fname, 'tfname': tfname, 'length': field['length'], 'type':'DATE', 'alias':falias})
            elif ftype == 'esriFieldTypeSmallInteger':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'SHORT', 'alias':falias})
            elif ftype == 'esriFieldTypeInteger':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'LONG', 'alias':falias})
            elif ftype == 'esriFieldTypeFloat':
                inFields.append({'fname': fname, 'tfname': tfname, 'length': 0, 'type':'FLOAT', 'alias':falias})
            elif ftype == 'esriFieldTypeOID':
                oid_field = fname

        # ******************************************************************    
        # Exporting All / Getting Feature Count ArcGIS Server 10.0 or newer
        # ******************************************************************         
        objectids = []
        oid_field = ""
        query_cnt = 0

        if debug: log_message("export_all: " + str(export_all));

        if ags10:
            if export_all:
                # User want to download all the features get list of Objectids (This only works for Server 10.0 or newer)
                f['returnIdsOnly'] = 'true'
                f['returnCountOnly'] = 'false'
                f['f'] = 'json'

                params = urllib.urlencode(f)

                req = urllib2.Request(inQueryURL, params)

                if authheader != "":
                    req.add_header("Authorization", authheader) 
                
                query_url = inQueryURL + params
                log_message("Get all the objectids: " + query_url)
                
                # Make the query
                furl = None
                try:
                    furl = urllib2.urlopen(req)
                except Exception as e:
                    raise Exception("Could not connect to server in URL");
                return_code = furl.getcode()
                if debug: log_message("return code: " + str(return_code))
                if return_code != 200:
                    raise Exception("Could not connect to query URL")
                resp = json.load(furl)

                if verbose_debug: log_message("RESP:" + str(resp))
                
                try:
                    error = resp['error']['message']
                    # Error was returned from the server
                    raise ValueError(str(resp))
                except ValueError:
                    raise Exception(str(resp))
                except Exception:
                    if debug: log_message("No Error Message from the server")

                try:
                    oid_field = resp['objectIdFieldName']
                    objectids = resp['objectIds']
                    query_cnt = len(objectids)
                    # Sort the objectids
                    objectids.sort()
                except:
                    # Server didn't return a objectid's
                    Exception("Couldn't get the objectids.")
                
            else:
                # Not exporting all so I'll try to get acount (This also only works for Server 10.0 or newer)
                if debug: log_message("f: " + str(f))           
                # Count query
                f['returnCountOnly'] = 'true'
                f['f'] = 'json'

                if debug: log_message("f: " + str(f))

                params =urllib.urlencode(f)

                req = urllib2.Request(inQueryURL, params)

                if authheader != "":
                    req.add_header("Authorization", authheader) 
                
                query_url = inQueryURL + params
                log_message("Get Counts Query: " + query_url)
                
                # Make the query
                furl = None
                try:
                    furl = urllib2.urlopen(req)
                except Exception as e:
                    raise Exception("Could not connect to server in URL");
                return_code = furl.getcode()
                if debug: log_message("return code: " + str(return_code))
                if return_code != 200:
                    raise Exception("Could not connect to query URL")
                resp = json.load(furl)

                try:
                    error = resp['error']['message']
                    # Error was returned from the server
                    raise ValueError(str(resp))
                except ValueError:
                    raise Exception(str(resp))
                except Exception:
                    if debug: log_message("No Error Message from the server")

                try:
                    query_cnt = resp['count']
                except:
                    # Server didn't return a count
                    log_message("Couldn't get the count.", "warn")

            log_message("Total records matching the query: " + str(query_cnt))        


        # **************************************************************************    
        # First data query used to collect data for creating output feature class
        # **************************************************************************                    

        # Force params
        f['returnCountOnly'] = 'false'
        f['returnIdsOnly'] = 'false'
        f['returnGeometry'] = 'true'
        f['f'] = 'json'
                        
        params = urllib.urlencode(f)

        req = urllib2.Request(inQueryURL, params)

        if authheader != "":
            req.add_header("Authorization", authheader) 

                        
        query_url = inQueryURL + params
        log_message("First Query: " + query_url)

        # Make the query
        furl = None
        try:
            furl = urllib2.urlopen(req)
        except Exception as e:
            raise Exception("Could not connect to server in URL");
        return_code = furl.getcode()
        if debug: log_message("return code: " + str(return_code))
        if return_code != 200:
            raise Exception("Could not connect to query URL")
        resp = json.load(furl)

        try:
            error = resp['error']['message']
            # Error was returned from the server
            raise ValueError(str(resp))
        except ValueError:
            raise Exception(str(resp))
        except Exception:
            if debug: log_message("No Error Message from the server")

        log_message("Building Feature Class")

        try:
            geometryType = resp['geometryType']
        except:
            # The layer doesn't have GeometryType defined set geometryType to None
            log_message("No geometryType found in query response.  This is typical of response for a Cached map service.")
            geometryType = None

        try:
            spatialReference = resp['spatialReference']
        except:
            # The layer doesn't have GeometryType defined set geometryType to None
            log_message("No spatialReference found in query response.  Might just be a table or undefined spatial reference.")
            spatialReference = None
            
        try:
            features = resp['features']
        except:
            # The layer doesn't have GeometryType defined can't export to Shapefile
            raise Exception("Features not found in response")

                            
        if debug: log_message("After JSON parsing")

        if geometryType == "esriGeometryPoint":
            geomType = "POINT"
        elif geometryType == "esriGeometryPolyline":
            geomType = "POLYLINE"
        elif geometryType == "esriGeometryPolygon":
            geomType = "POLYGON"
        elif geometryType == "esriGeometryMultipoint":
            geomType = "MULTIPOINT"
        else:
            geomType = None

        if debug: log_message("geomType: " + str(geomType) + ", geometryType: " + str(geometryType))

        # Create Spatial Reference from the return value
        fcSR = None
        if not spatialReference is None:
            # Create spatial ref from service response        
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

        # *******************************************************    
        # Create output file or feature class
        # *******************************************************                    
        fc = None

        ftabdelimited = None
        tabdelimitefilename = ""
        
        if outputFormat == "TABDELIMITEDFILE":
            # Create ftabdelimited
            tabdelimitefilename = os.path.join(output_workspace,output_fcname + ".tab")
            ftabdelimited = codecs.open(tabdelimitefilename, "w",encoding='utf-8')
            fvals = []
            for field in inFields:
                fvals.append(field['tfname'])
            
            line = "\t".join(fvals) + "\n"
            ftabdelimited.write(line)
        else:
            # Clear out stuff in memory from previous runs
            try:
                arcpy.Delete_management(r'in_memory\temp')
            except:
                if verbose_debug: "Failed delete in_memory\temp.  Probably OK because it doesn't exist"

            try:
                arcpy.Delete_management(r'in_memory\clip')
            except:
                if verbose_debug: "Failed delete in_memory\clip.  Probably OK because it doesn't exist"

            try:
                arcpy.Delete_management(r'in_memory\tempclip')
            except:
                if verbose_debug: "Failed delete in_memory\tempclip.  Probably OK because it doesn't exist"
            
            if geomType is None:
                # If we have null geom's make them points if the user requested feature classes
                fc = arcpy.CreateFeatureclass_management(r'in_memory', "temp", "POINT", '#', 'DISABLED', 'DISABLED', fcSR)
            else:
                fc = arcpy.CreateFeatureclass_management(r'in_memory', "temp", geomType, '#', 'DISABLED', 'DISABLED', fcSR)

            if debug: log_message("fc: " + str(fc))

            # Shapefile must have at least one attribue field the CreateFeatureclass method above creates a field named "ID"
            
            field_count = 0
            has_id_field = False

            if outputFormat == "SHAPEFILE" or outputFormat == "DBASEFILE":
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
                        
                    
                    if debug:
                        vfname = arcpy.ValidateFieldName(fname,output_workspace)
                        if fname != vfname:                            
                            log_message("Field Name: " + fname)
                            log_message("Valid Field Name: " + vfname)

                    arcpy.AddField_management(fc, fname, ftype, '#', '#', flen, falias)
                    field_count += 1


            log_message("Feature Class Created")
            

            # Create a cursor to the output feature class to write features to
            iCur = arcpy.InsertCursor(fc)


        # *******************************************************    
        # Create output log file
        # *******************************************************                    

        # Create a log file for outputing any features rejected
        logfilename = output_fcname + "_log.txt"
        fout = open(os.path.join(output_folder,logfilename), "w")        

        # Output warning to output log file 
        if outputFormat == "SHAPEFILE" or outputFormat == "DBASEFILE":
            fout.write(shapefile_warning)

        # Based on a single query with 1=1 how many features were returned (Limited by the server)
        max_features_returned = len(features)
        
        if export_all and ags10:
            # *******************************************************    
            # Export all features (requires ArcGIS Server 10 or newer)
            # *******************************************************
            # Only applies if the ags10 is also true
            log_message("Begin Exporting All")
            fout.write("**** Begin Exporting All ****\n")

            if len(objectids) == 0:
                raise Exception("Service returned no features")

            everything = False
            #"".join(f['where'].split())  This will strip out all white space
            # f['where'].replace(" ","")  This takes out just spaces
            if f['where'].replace(" ","") == "1=1":
                everything = True
            # If the where is 1=1 then we can use ranges of OIDS in URL and http get
            # Otherwise; we'll use a where with OID in [list of OIDS]; this approach requires HTTP POST
                             
            if debug:
                log_message("everything: " + str(everything))
                log_message("where: " + f['where'])

            features_processed = 0
            
            more_ids = True
            i = 0

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

                if min_objectid < 0:
                    raise Exception("Service problem. Service returned an ObjectID less than 0", "warn")

                if max_objectid <= min_objectid:
                    raise Exception("Service problem. Invalid ObjectID values","warn")

                features_processed += (lastindex - i)
                if debug: log_message("features_processed = " + str(features_processed))

                where = ""
                if everything:
                    # Use a range of oids from min_objectid to max_objectid
                    where = oid_field + ">=" + str(min_objectid) + " and " + oid_field + "<" + str(max_objectid)
                else:
                    oids = "(" + ",".join(map(str,objectids[i:lastindex])) + ")"                
                    if verbose_debug: log_message("oids: " + oids)
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
                        # If everything use HTTP GET it's shorter
                        req = urllib2.Request(inQueryURL, params)
                        if authheader != "":
                            req.add_header("Authorization", authheader)                         
                        furl = urllib2.urlopen(req)
                    else:
                        # Use HTTP POST if request is OID in (list of OIDS); GET won't support such a long input
                        req = urllib2.Request(inQueryURL)
                        if authheader != "":
                            req.add_header("Authorization", authheader) 
                        furl = urllib2.urlopen(req, params, TIMEOUTSECS)
                except Exception as e:
                    raise Exception("Could not connect to server in URL");
                return_code = furl.getcode()
                if debug: log_message("return code: " + str(return_code))
                if return_code != 200:
                    raise Exception("Could not connect to query URL")

                try:
                    resp = json.load(furl)
                except Exception as e:
                    if debug: log_message("Error: " + str(e), "warn")


                try:
                    features = resp['features']
                except:
                    # The layer doesn't have GeometryType defined can't export to Shapefile
                    raise Exception("Features not found in response")

                if outputFormat == "TABDELIMITEDFILE":
                    num_features_inserted += exportTabDelimited(features, inFields, ftabdelimited, fout)
                else:
                    num_features_inserted += exportFeatures(iCur, features, inFields, geomType, fcSR, outputFormat, shpNullTypes, fout)
            
                if (time.time() - start_time) > max_run_secs and not desktop:
                    # The ideal is to stop before the SOC times out and send the user what I was able to extract
                    log_message("************************************************", "warn")
                    log_message("Times up.  For full export you might need to run the desktop version.", "warn")
                    log_message("************************************************", "warn")
                    break
                i = i + max_features_returned


                            
            fout.write("**** End Exporting All ****\n")
            log_message("End Exporing All")
        else:
            # *******************************************************    
            # Export features (whatever one call returns)
            # *******************************************************            
            log_message("Begin Exporting")
            
            if len(features) < query_cnt:
                log_message("************************************************", "warn")
                log_message("Map Service only returned " + str(max_features_returned) + " of " + str(query_cnt) + " features matching your query.", "warn")
                log_message("************************************************", "warn")

                fout.write("Map Service only returned " + str(max_features_returned) + " of " + str(query_cnt) + " features matching your query.\n")
            fout.write("**** Features rejected ****\n")

            if outputFormat == "TABDELIMITEDFILE":
                num_features_inserted = exportTabDelimited(features, inFields, ftabdelimited, fout)                    
            else:
                num_features_inserted = exportFeatures(iCur, features, inFields, geomType, fcSR, outputFormat, shpNullTypes, fout)            
            fout.write("**** End Features rejected ****\n")
            log_message("Export Complete")

        if ags10:
            fout.write("Number of features added: " + str(num_features_inserted) + " of " + str(query_cnt))
            if debug: log_message("Number of features added: " + str(num_features_inserted) + " of " + str(query_cnt))
        else:
            fout.write("Number of features added: " + str(num_features_inserted))
            if debug: log_message("Number of features added: " + str(num_features_inserted))
                
        if debug: log_message("Output FC Name: " + output_fcname)

        if geomType == "POINT" and clip:
            log_message("Clipping has no effect on POINT geometries.")
            clip = False

        # *******************************************************    
        # Create a clip feature class if user requested clip 
        # *******************************************************     

        clipshpfile = None
        if outputFormat in ["SHAPEFILE", "FILEGEODATABASE", "PERSONALGEODATABASE"]:
            if clip:
                if debug: log_message("clipPoly:" + str(clipPoly))
                # In order to clip we need to create a feature class with clip geometry and project to outSR (fcSR)
                clipfc = arcpy.CreateFeatureclass_management(r'in_memory', "clip", "POLYGON", '#', 'DISABLED', 'DISABLED', inSR)
                clipCur = arcpy.InsertCursor(clipfc)
                clipRow = clipCur.newRow()
                clipRow.Shape = clipPoly
                clipCur.insertRow(clipRow)
                del clipRow
                del clipCur
                clipshpfile = os.path.join(output_folder,"clip.shp")
                arcpy.Project_management("in_memory\clip",clipshpfile,fcSR)
                
        # *****************************************************************    
        # Copy the feature class from mememory to disk (Clip if requested)
        # *****************************************************************     
        
        # Copy from memory to disk
        if outputFormat == "TABDELIMITEDFILE":
            # Tab Delimited File
            fc = tabdelimitefilename
        elif outputFormat == "SHAPEFILE":
            # Getting ready to output
            arcpy.env.workspace = output_folder

            # Shapefile name to create
            #output_shapefilename = r"output.shp"
            output_shapefilename = output_fcname + ".shp"

            # Create Feature Class
            if clip:
                fc = arcpy.Clip_analysis(r'in_memory\temp', clipshpfile, r'in_memory\tempclip')
                fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\tempclip', output_workspace, output_shapefilename)
            else:
                fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\temp', output_workspace, output_shapefilename)
        elif outputFormat == "DBASEFILE":
            # Getting ready to output
            arcpy.env.workspace = output_folder

            # dbase file name to create
            output_dbasefilename = output_fcname + ".dbf"

            # Create Feature Class
            fc = arcpy.TableToTable_conversion(r'in_memory\temp', output_workspace, output_dbasefilename)
            
        elif outputFormat == "FILEGEODATABASE":
            # Create File Geodatabase
            try: 
                if debug:
                    log_message("output_workspace: " + str(output_workspace))
                    log_message("output_fcname: " + str(output_fcname))

                if clip:
                    fc = arcpy.Clip_analysis(r'in_memory\temp', clipshpfile, r'in_memory\tempclip')
                    fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\tempclip', output_workspace, output_fcname)                    
                else:
                    fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\temp', output_workspace, output_fcname)
            except:
                raise Exception("Could not copy to File Geodatabase")                        

        elif outputFormat == "FILEGEODATABASETABLE":
            # Create File Geodatabase Table
            try: 
                if debug:
                    log_message("output_workspace: " + str(output_workspace))
                    log_message("output_fcname: " + str(output_fcname))
                fc = arcpy.TableToTable_conversion(r'in_memory\temp', output_workspace, output_fcname)
            except:
                raise Exception("Could not copy to File Geodatabase Table")                        

        elif outputFormat == "PERSONALGEODATABASE":
            # Create Personal Geodatabase
            try: 
                if clip:
                    fc = arcpy.Clip_analysis(r'in_memory\temp', clipshpfile, r'in_memory\tempclip')
                    fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\tempclip', output_workspace, output_fcname)                    
                else:
                    fc = arcpy.FeatureClassToFeatureClass_conversion(r'in_memory\temp', output_workspace, output_fcname)                              
            except:
                raise Exception("Could not create Personal Geodatabase")                                    

        elif outputFormat == "PERSONALGEODATABASETABLE":
            # Create File Geodatabase Table
            try: 
                if debug:
                    log_message("output_workspace: " + str(output_workspace))
                    log_message("output_fcname: " + str(output_fcname))
                fc = arcpy.TableToTable_conversion(r'in_memory\temp', output_workspace, output_fcname)
            except:
                raise Exception("Could not copy to Personal Geodatabase Table")                        

        else:
            raise Exception("Exception unsupported output format")

        # *******************************************************    
        # Populate the result with sucessful results
        # *******************************************************     
        
        result['num_features_inserted'] = num_features_inserted
        result['message'] = ""
        result['ok'] = True
        result['fc'] = fc


    except Exception as e:
        # *******************************************************    
        # Populate the result with error results
        # *******************************************************        
        if debug: log_message("ERROR: " + str(e))
        # output failed to create return -1
        result['num_features_inserted'] = -1
        result['message'] = str(e)
        result['ok'] = False
        result['fc'] = None

    finally:

        # *******************************************************    
        # Clean up and return result
        # *******************************************************
        
        if ftabdelimited:
            try:
                ftabdelimited.close()
            except:
                if debug: log_message("ftabdelimited failed to close.")

        if fout:
            try:
                fout.close()
            except:
                if debug: log_message("fout failed to close.")
                        
        try:
            # For some reason del iCur leaves locks
            # The Following line fails; however, it remove the locks
            # These locks will prevent the service from working with "Local Jobs Directory"
            arcpy.CreateFileGDB_management("in_memory","whatever","9.3")
        except:
            log_message("OK: Clearing the locks")            
        if debug: log_message("End: " + strftime(time_fmt, localtime()))

        if iCur:
            del iCur

        return result             


def getDate(timestamp_milliseconds):
    # *******************************************************    
    # Created this function to handle dates before and after 1 Jan 1970
    # *******************************************************
        
    dt = None
    if timestamp_milliseconds >= 0:
        dt = datetime.datetime.utcfromtimestamp(timestamp_milliseconds / 1000)
    else:
        # date prior to epoch
        epoch = datetime.datetime.utcfromtimestamp(0)
        # flip the date over Epoch (Python doesn't support negative timestamps)
        dt = datetime.datetime.utcfromtimestamp(-timestamp_milliseconds / 1000)
        # find the distance from epoch to flip
        diff = dt - epoch        
        dt = epoch - diff
    return dt
        

def exportTabDelimited(features, inFields, ftabdelimited, fout):
    # *******************************************************    
    # Export to tab delimited file
    # *******************************************************
    i = 0
    num_features_inserted = 0
    for feature in features:
        try:
            attr = feature['attributes']
            fvals = []
            for field in inFields:
                ftype = field['type']
                fval = attr[field['fname']]
                if ftype == 'DATE':
                    # Convert the number of milliseconds from epoch to string date for databases
                    fval = getDate(fval).strftime("%m/%d/%Y %I:%M:%S %p")
                    if verbose_debug: log_message(fval)
                fvals.append(fval)        
            line = "\t".join(map(unicode,fvals)) + "\n"
            ftabdelimited.write(line)
            num_features_inserted += 1
        except Exception as e:
            msg = "Feature Failed to Export: " + str(e) + "\n"
            msg += str(feature) + "\n"
            if debug: log_message(msg)
            fout.write(msg)
        finally:
            i += 1
            if i % 10 == 0:
                if verbose_debug: log_message("Feature " + str(i) + ": " + strftime(time_fmt, localtime()))            
            
    return num_features_inserted    

def exportFeatures(iCur, features, inFields, geomType, fcSR, outputFormat, shpNullTypes, fout):
    # *******************************************************    
    # Export Features
    # *******************************************************    
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
                flen = field['length']

                if outputFormat == "SHAPEFILE" or outputFormat == "DBASEFILE":
                    if fval is None:
                        if verbose_debug: log_message("fval Before: " + str(fval))
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

                        if verbose_debug: log_message("fval After: " + str(fval) + " " + ftype)
                    else:
                        if ftype == 'DATE':
                            # Convert the number milliseconds from epoch to string date
                            fval = getDate(fval).strftime("%d/%m/%Y")
                        elif ftype == 'TEXT':
                            # Truncate value to 254 characters max allowed for shapefiles if not null
                            fval = fval[:flen]
                            
                else:
                    # Not a Shapefile or DBasefile

                    if fval is None:
                        if verbose_debug: log_message("Null ok for File or Personal Geodatabases")
                    else:
                        if ftype == 'DATE':
                            # Convert the number of milliseconds from epoch to string date for databases
                            fval = getDate(fval).strftime("%m/%d/%Y %I:%M:%S %p")
                        elif ftype == 'TEXT':
                            # Truncate value to 254 characters max allowed for shapefiles if not null
                            fval = fval[:flen]
                        


                if verbose_debug: log_message("Final Date fval: " + str(fval) + " " + field['tfname'])
                feat.setValue(field['tfname'], fval)

            if geomType is None:
                if verbose_debug: log_message("geomType is None")

            elif geomType == "POLYLINE":
                point = arcpy.Point()
                sub_array = arcpy.Array()
                array = arcpy.Array()
                try:
                    geometry = feature['geometry']
                    coordList = geometry['paths']

                    for f in coordList:
                        for coordPair in f:
                            point.X = coordPair[0]
                            point.Y = coordPair[1]
                            array.add(point)
                        array.append(sub_array)

                        sub_array.removeAll()

                    if fcSR is None:
                        polyline = arcpy.Polyline(array)
                    else:
                        polyline = arcpy.Polyline(array, fcSR)

                    feat.shape = polyline
                except:
                    log_message("Problem creating polyline geometry for: " + str(feature),"warn")
                    log_message("Setting geometry to null")
                finally:
                    array.removeAll()
                    sub_array.removeAll()

                    
            elif geomType == "POLYGON":
                
                point = arcpy.Point()
                sub_array = arcpy.Array()
                array = arcpy.Array()
                
                try:
                    geometry = feature['geometry']
                    coordList = geometry['rings']

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

                    if fcSR is None:
                        polygon = arcpy.Polygon(array)
                    else:                        
                        polygon = arcpy.Polygon(array, fcSR)

                    feat.shape = polygon
                except:
                    log_message("Problem creating polygon geometry for: " + str(feature),"warn")
                    log_message("Setting geometry to null")
                finally:
                    array.removeAll()
                    sub_array.removeAll()
                    
                
            elif geomType == "POINT":
                try:
                    geometry = feature['geometry']
                    
                    point = arcpy.Point()

                    point.X = geometry['x']
                    point.Y = geometry['y']
                    
                    if fcSR is None:
                        pointGeom = arcpy.PointGeometry(point)    
                    else:
                        pointGeom = arcpy.PointGeometry(point, fcSR)
                                        
                    feat.shape = pointGeom
                except:
                    log_message("Problem creating point geometry for: " + str(feature),"warn")
                    log_message("Setting geometry to null")
                
            elif geomType == "MULTIPOINT":

                point = arcpy.Point()
                array = arcpy.Array()
                try:
                    geometry = feature['geometry']
                    coordList = geometry['points']

                    for coordPair in coordList:
                        point.X = coordPair[0]
                        point.Y = coordPair[1]
                        array.add(point)

                    if fcSR is None:    
                        multiPoint = arcpy.Multipoint(array)
                    else:
                        multiPoint = arcpy.Multipoint(array, fcSR)

                    feat.shape = multiPoint
                except:
                    log_message("Problem creating multi-point geometry for: " + str(feature),"warn")
                    log_message("Setting geometry to null")
                finally:
                    array.removeAll()
                    
                
            iCur.insertRow(feat)
            num_features_inserted += 1

        except Exception as e:
            msg = "Feature Failed to Export: " + str(e) + "\n"
            msg += str(feature) + "\n"
            if debug: log_message(msg)
            fout.write(msg)
        finally:
            if feat:
                del feat
            i += 1
            if i % 10 == 0:
                if verbose_debug: log_message("Feature " + str(i) + ": " + strftime(time_fmt, localtime()))
    return num_features_inserted
            

def makeLayerList(layerids):
    # *******************************************************    
    # Create layerlist from comma sep list and ranges
    # e.g.  1,2,4-8,10-14,20  => 1,2,4,5,6,7,8,10,11,12,13,14,20
    # *******************************************************
    layerList = []
    try:
    
        layerids = layerids.strip()

        if layerids == "":
            raise Exception("Empty layerids string")

        layeridsParts = layerids.split(",")

        for layeridPart in layeridsParts:
            if layeridPart == "":
                # Empty layeridPart; extra commas
                continue
                
        
            layeridPartDash = layeridPart.split("-")
            partcnt = len(layeridPartDash)
            if partcnt == 1:
                # No dash assume it's a single number
                try:
                    layerid = int(layeridPart)
                except ValueError:
                    # Must be numbers
                    raise Exception("Invalid layer id: " + layeridPart)
                if not layerid in layerList:
                    layerList.append(layerid)
            elif partcnt == 2:
                # This is a range
                try:
                    lownum = int(layeridPartDash[0])
                except ValueError:
                    # Must be numbers
                    raise Exception("Invalid start number: " + layeridPart)
                try:
                    highnum = int(layeridPartDash[1])
                except ValueError:
                    # Must be numbers
                    raise Exception("Invalid end number: " + layeridPart)

                if highnum < lownum:
                    raise Exception("Invalid range: " + layeridPart)
                
                for i in range(lownum, highnum + 1):
                    if not i in layerList:
                        layerList.append(i)
                
            else:
                # invalid input
                print "Invalid part: " + layeridPart
                
        if len(layerList) == 0:
            raise Exception("Empty layerid list")

        return layerList
    except Exception as e:
        return str(e)

def zipfolder(folder, zipFile):
    '''
    This function fips all the files in a folder
    It will go one folder deep and add those to the zip
    ".lock" files are excluded by default
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

if __name__ == "__main__":
    try:
        arcpy.Delete_management(r"C:\Temp\temp.gdb\BoreholeTemperature")
    except:
        print "OK"
    inQueryURL = r"http://maps.stlouisco.com/ArcGIS/rest/services/Maps/Parcels/MapServer/0"
    inQueryParams = '{"exportAll":"False","outFields":"*"}'
    inOutputFormat = "FILEGEODATABASE"
    shpNullTypes = '{"short": 0, "text": "", "float": 0.0, "long": 0, "double": 0.0, "date": "01/01/1970"}'
    output_folder = r"C:\Temp"
    output_workspace = r"C:\Temp\temp.gdb"
    desktop = True
    authheader = ""
    clip = False
    exportMapServerLayer(inQueryURL, inQueryParams, inOutputFormat, shpNullTypes, \
                         output_folder, output_workspace, desktop, authheader, clip)
