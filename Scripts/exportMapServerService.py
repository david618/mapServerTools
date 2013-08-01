import arcpy, os, sys, traceback, uuid, zipfile
from arcpy import env
import time, datetime
from time import strftime, localtime
import urllib2,json
import base64
from urlparse import urlparse

from exportCommon import log_message,exportMapServerLayer,zipfolder,makeLayerList

# Set to desktop for running from desktop
desktop = False

# Set debug and/or verbose_debug for debugging purposes
debug = False
verbose_debug = False

# Set True and set array of valid services to limit what servers can be exported from
# SECURITY WARNING: Users can specify a internal server for export if they know the name (e.g. localhost, ags10a)
check_valid_servers = False
valid_servers = []
valid_servers.append(r"http://localhost:8399")
valid_servers.append(r"http://12.187.20.60")
valid_servers.append(r"http://ags10a")

if __name__ == '__main__':

    try:
        # Main Function this is where things start   (Get  parameters from the GP)
        inMapServerURL = arcpy.GetParameterAsText(0).strip() # Service URL
        inLayers = arcpy.GetParameterAsText(1).strip() # Optional Layer list default is all layers 
        inQueryParams = arcpy.GetParameterAsText(2).strip() # Query Parametrs as JSON 
        inOutputFormat = arcpy.GetParameterAsText(3).strip() # Format (Shapefile, FileGeodatabase, PersonalGeodatabase)
        inShapefileNulls = arcpy.GetParameterAsText(4).strip()  # JSON String
        inClip = arcpy.GetParameterAsText(5).strip()   # Clip True or False
        if desktop:
            # Desktop version supports HTTP Basic Authentication
            inUsername = arcpy.GetParameterAsText(6).strip()  # Username required to access the MapServer Service
            inPassword = arcpy.GetParameterAsText(7).strip()  # Password required to access the MapServer Service
        else:
            inUsername = ""
            inPassword = ""
        # NOTE: If you add a parameter make sure to update the output index at end of script

        # **************************
        # Parse and Check Inputs
        # **************************


        # ***** Parse inClip *****
        clip = False
        if inClip.upper() == 'TRUE':   
            clip = True

        # ***** Parse inLayers *****
        layerList = []
        layerListSpecified = False
        if inLayers != "":
            layerList = makeLayerList(inLayers)
            if type(layerList) is str:
                raise Exception("inLayers must be a comma separated list of layer numbers or layer ranges.")
            else:
                layerList.sort()
                if debug: log_message("layerList: " + str(layerList))
                layerListSpecified = True            
        if debug: log_message("layerList: " + str(layerList))

        # ***** Parse inQueryParams *****
        # Set Default queryParsm to empty dictionary.
        queryParams = "{}"   
        if inQueryParams != "":
            queryParams = inQueryParams          
        if debug: log_message("queryParams: " + str(queryParams))
        

        # ***** Parse inShapefileNulls *****
        # Default Shapefile Nulls
        shapefileNulls = {}
        shapefileNulls['date'] = "01/01/1970"
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
                        if a == "short" or a == "long":                        
                            shapefileNulls[a] = int(shpnulls[a])
                        elif a == "date" or a == "text":
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


        # ***** Parse inOutputFormat *****
        # Default to File Geodatabase
        outputFormat = "FILEGEODATABASE"  
        if inOutputFormat != "":
            # upper to make the input Case Insensitive
            outputFormat = inOutputFormat.upper()
        if debug: log_message("outputFormat: " + str(outputFormat))

        # ***** Parse inMapServerURL *****
        # Strip off any params stuck onto the URL
        a = urlparse(inMapServerURL)

        server = ""
        try:
            server = a.scheme + "://" + a.netloc + a.path
            if debug: log_message("Server: " + server)
        except:
            raise Exception("Unable to parse inMapServerURL")

        if check_valid_servers:    
            if server in valid_servers:
                # Change the path to an internal path for export
                inMapServerURL = "http://localhost:8399" + a.path
            else:
                raise Exception("Unsupported server.  The following servers are supported: " + str(valid_servers))

        # **************************
        # Get Service Info (just add ?f=json to the inMapServerURL)
        # **************************
        
        query_url = inMapServerURL + "?f=json"
        if debug: log_message("Get Service Info: " + query_url)

        req = urllib2.Request(query_url)

        # ***** Build authheader for HTTP  Basic Authentication *****
        authheader = ""
        
        if inUsername != "":
            base64string = base64.encodestring('%s:%s' % (inUsername, inPassword))[:-1]
            authheader =  "Basic %s" % base64string
            req.add_header("Authorization", authheader)              

        # **** Query Map Service to get information ****
        furl = None
        try:
            furl = urllib2.urlopen(req)
        except Exception as e:
            raise Exception("Could not connect to server in URL. " + str(e));
        return_code = furl.getcode()
        if debug: log_message("return code: " + str(return_code))
        if return_code != 200:
            if return_code >= 400 and return_code < 500:
                raise Exception("Could not connect to server in URL. Access denied. Return Code: " + str(return_code))
            elif return_code >= 500 and return_code < 600:
                raise Exception("Could not connect to server in URL. Server Error. Return Code: " + str(return_code))
            else:
                raise Exception("Could not connect to server in URL. Return Code: " + str(return_code))

        try:
            resp = json.load(furl)
        except:
            raise Exception("Could not process json returned from the service.")
        
                
        mapName = ""
        try:
            mapName = resp['mapName']
        except:
            # Use default name Layers
            mapName = "Layers"

                
        layers = []
        # Get list of valid layers      
        try:
            layers = resp['layers']
        except:
            if debug: log_message("Service has no layers")

        tables = []        
        # Get list of valid tables      
        try:
            tables = resp['tables']
        except:
            if debug: log_message("Service has no tables")

        # Total number of layers and tables
        num_layers_and_tables = len(layers) + len(tables)

        if num_layers_and_tables == 0:
            # If it's still empty we're done
            raise Exception("No layers or tables to export. Could be a problem with the Map Service.")

        if desktop:
            # For desktop make the scratch folder 
            scriptPath = sys.path[0]
            toolSharePath = os.path.dirname(scriptPath)
            scratchPath = os.path.join(toolSharePath, "Scratch")
            if not os.path.exists(scratchPath):
                # Create Scratch folder if needed
                os.mkdir(scratchPath)
        else:
            # For service use the environment scratch workspace
            scratchPath = env.scratchWorkspace            
                
        if debug: log_message("scratchPath: " + scratchPath)

        # Create a random output folder
        rndFolderName = str(uuid.uuid4());        
        outFolder = os.path.join(scratchPath, rndFolderName)
        os.mkdir(outFolder)
        if debug: log_message("outFolder: " + outFolder)

        # Create the output workspace
        outWorkspace = ""
        if outputFormat == "SHAPEFILE" or outputFormat == "DBASEFILE" or outputFormat == "TABDELIMITEDFILE":
            try:
                # Create Folder as Workspace for Shapefile(s)
                outWorkspace = os.path.join(outFolder, "export")
                os.mkdir(outWorkspace)
            except:
                raise Exception("Could not create Folder for file output.")
        elif outputFormat == "FILEGEODATABASE" or outputFormat == "FILEGEODATABASETABLE":
            # Create File Geodatabase (use 9.3 for maxium compatibility)
            try: 
                outWorkspace = arcpy.CreateFileGDB_management(outFolder, "export", "9.3")
            except:
                raise Exception("Could not create File Geodatabase")                        

        elif outputFormat == "PERSONALGEODATABASE" or outputFormat == "PERSONALGEODATABASETABLE":
            # Create Personal Geodatabase (use 9.3 for maxium compatibility)
            try:                
                outWorkspace = arcpy.CreatePersonalGDB_management(outFolder, "export", "9.3")
            except:
                raise Exception("Could not create Personal Geodatabase")                                    
        else:
            raise Exception("Exception unsupported output format")

        # Loop through the layers and export each layer
        total_features_exported =  0
        for layer in layers:
            if verbose_debug: log_message("layer: " + str(layer))
            if layer['subLayerIds'] is None:
                # if subLayerIds is not None it's a group layer                
                layerid = layer['id']
                if layerListSpecified:                    
                    if not (layerid in layerList):
                        # Warn the user and continue
                        if debug: log_message("Layerid not found in Service: " + str(layerid), "warn")
                        continue                
                layername = layer['name']
                # Output the Layer currently being exported
                log_message("Exporting : " + layername + " (" + str(layerid) + ")")

                queryURL = inMapServerURL + "/" + str(layerid)
                a = exportMapServerLayer(queryURL, queryParams, outputFormat, shapefileNulls, outFolder, outWorkspace, desktop, authheader, clip)

                if debug: log_message("a: " + str(a))
                if not a['ok']:
                    log_message(a['message'], "warn")

                if a['num_features_inserted'] <= 0:
                    log_message("No features exported","warn")
                else:
                    total_features_exported += a['num_features_inserted']

                if debug: log_message("fc: " + str(a['fc']))  

        for table in tables:                                
            layerid = table['id']
            if layerListSpecified:                
                if not (layerid in layerList):
                    # Not in layerList continue with next layer
                    continue
            
            layername = table['name']
            log_message("Exporting : " + layername + " (" + str(layerid) + ")")
            queryURL = inMapServerURL + "/" + str(layerid)
            try:
                a = exportMapServerLayer(queryURL, queryParams, outputFormat, shapefileNulls, outFolder, outWorkspace, desktop, authheader)
                if debug: log_message("a: " + str(a))
                if not a['ok']:
                    log_message(a['message'], "warn")

                if a['num_features_inserted'] <= 0:
                    log_message("No features exported","warn")
                else:
                    total_features_exported += a['num_features_inserted']

                if debug: log_message("fc: " + str(a['fc']))  
            except Exception as e:
                log_mesage("Export call failed: " + str(e))

        if total_features_exported == 0:
            # Nothing exported return Error Message
            raise Exception("No feature matching your query were exported.")

        if desktop:
            # Don't zip and retun the Folder
            arcpy.SetParameterAsText(8, outFolder)

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
            arcpy.SetParameterAsText(6, outfile)
        

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

