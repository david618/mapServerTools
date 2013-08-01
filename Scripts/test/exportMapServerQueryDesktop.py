import arcpy, os, sys, traceback, uuid, zipfile
from arcpy import env
import urllib,json,datetime
from time import strftime, localtime
from urlparse import urlparse
import time


from exportCommon import log_message,exportMapServerLayer,zipfolder

# Set to desktop for running from desktop
desktop = True

debug = False

verbose_debug = False


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

        # Set Defaults for empty input
        # Query Params to empty 
        queryParams = "{}"   
        if inQueryParams != "":
            queryParams = inQueryParams            
        if debug: log_message("queryParams: " + str(queryParams))


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

        # Default to File Geodatabase
        outputFormat = "FILEGEODATABASE"  
        if inOutputFormat != "":
            outputFormat = inOutputFormat.upper()
        if debug: log_message("outputFormat: " + str(outputFormat))        


        # Strip off any params stuck onto the URL
        a = urlparse(inQueryURL)

        server = a.scheme + "://" + a.netloc
        if debug: log_message("Server: " + server)

        urlWithoutParams = server + a.path
        urlWithoutParams =  inQueryURL
        
        if check_valid_servers:    
            if not server in valid_servers:
                raise Exception("Unsupported server.  The following servers are supported: " + str(valid_servers))


        if desktop:
            # Use this when testing from Desktop
            scriptPath = sys.path[0]
            toolSharePath = os.path.dirname(scriptPath)
            scratchPath = os.path.join(toolSharePath, "Scratch")
            if not os.path.exists(scratchPath):
                # Create Scratch folder if needed
                os.mkdir(scratchPath)
        else:
            # Use this when deployed as GP Service
            scratchPath = env.scratchWorkspace            
                
        if debug: log_message("scratchPath: " + scratchPath)

        # Create a random output folder
        rndFolderName = str(uuid.uuid4());
        
        outFolder = os.path.join(scratchPath, rndFolderName)

        os.mkdir(outFolder)

        if debug: log_message("outFolder: " + outFolder)

        outWorkspace = ""

        # Create the output workspace
        if outputFormat == "SHAPEFILE" or outputFormat == "DBASEFILE" or outputFormat == "TABDELIMITEDFILE":
            try:
                # Create Folder as Workspace for Shapefile(s)
                outWorkspace = os.path.join(outFolder, "export")
                os.mkdir(outWorkspace)
            except:
                raise Exception("Could not create Folder for file output.")
        elif outputFormat == "FILEGEODATABASE" or outputFormat == "FILEGEODATABASETABLE":
            # Create File Geodatabase as Workspace
            try: 
                outWorkspace = arcpy.CreateFileGDB_management(outFolder, "export", "9.3")
            except:
                raise Exception("Could not create File Geodatabase")                        

        elif outputFormat == "PERSONALGEODATABASE" or outputFormat == "PERSONALGEODATABASETABLE":
            # Create Personal Geodatabase
            try: 
                outWorkspace = arcpy.CreatePersonalGDB_management(outFolder, "export", "9.3")
            except:
                raise Exception("Could not create Personal Geodatabase")                                    
        else:
            raise Exception("Exception unsupported output format")

        
        a = exportMapServerLayer(urlWithoutParams, queryParams, outputFormat, shapefileNulls, outFolder, outWorkspace, desktop)

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

