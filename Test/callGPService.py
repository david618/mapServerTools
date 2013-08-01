import arcpy,sys,traceback
import urllib,json,os
import time,datetime
from time import strftime, localtime

# For additional messages
debug = False

# Set this to where you want the zip file to be saved
output_folder = r"C:\Temp"

# How frequently to check for status changes
check_interval_secs = 10

def submitJob(gp_service_url, params):
    
    try:
        # Add or set parameter for json respons
        params['f'] = "json"
        
        # Encode the parameters
        url_params = urllib.urlencode(params)        

        # Add the submitJob gp_service_url
        query_url = gp_service_url + "/submitJob?" + url_params
        
        print "Submit Job URL: " + query_url

        # Submit Job
        furl = None
        try:
            furl = urllib.urlopen(query_url)
        except Exception as e:
            raise Exception("Could not connect to server in URL");
        return_code = furl.getcode()
        if return_code != 200:
            raise Exception("Could not connect to query URL")
        resp = json.load(furl)

        # Get the jobStaus and jobId from the response        
        jobStatus = None
        jobId = None
        try:
            jobStatus = resp['jobStatus']
            jobId = resp['jobId']
        except:
            # Error was returned from the server
            raise Exception("Failed to submit job")

        # Get start time 
        start_time = time.time()

        # Build the jobs query
        query_url = service_url + "/jobs/" + jobId + "?f=json"
        print "Job Details URL: " + query_url


        # Wait for the job to finish        
        while jobStatus != "esriJobSucceeded" and jobStatus != "esriJobFailed":
            time.sleep(check_interval_secs)          
            # Get the jobStatus
            furl = None
            try:
                furl = urllib.urlopen(query_url)
            except Exception as e:
                raise Exception("Could not connect to server in URL");
            return_code = furl.getcode()
            if return_code != 200:
                raise Exception("Could not connect to query URL")
            resp = json.load(furl)

            print "Elapsed Time: " + str(time.time() - start_time) + " seconds"
            
            try:
                error = resp['error']
                # Error was returned from the server
                raise Exception("Failed to submit job")
            except:
                if debug: print "No Error"

            try:
                jobStatus = resp['jobStatus']                
            except:
                # Error was returned from the server
                raise Exception("Failed to get status")

        print "Job took " + str(time.time() - start_time) + " seconds"

        msgs = resp['messages']
        for msg in msgs:
            print(str(msg))

        print "Test Results: "
        # Last couple of messages show final results 
        print msgs[-1]['description']
        print msgs[-2]['description']

            
        if jobStatus == "esriJobSucceeded":
            # Download the resulint zip file
            zip_filename = os.path.join(output_folder, testname + ".zip")

            paramUrl = resp['results']['outZipFile']['paramUrl']

            # Query to retrieve the zip file path
            query_url = service_url + "/jobs/" + jobId + "/" + paramUrl + "?f=json"
            print "paramURL: " + query_url
            
            furl = None
            try:
                furl = urllib.urlopen(query_url)
            except Exception as e:
                raise Exception("Could not connect to server in URL");
            return_code = furl.getcode()
            if return_code != 200:
                raise Exception("Could not connect to query URL")
            resp = json.load(furl)

            # Give the server a few seconds 
            time.sleep(check_interval_secs)


            query_url = resp['value']['url']
            print "Zip File URL: " + query_url

            # Download zip file
            furl = None
            try:
                furl = urllib.urlopen(query_url)
                fout = open(zip_filename, 'wb')
                
                block_sz = 8192
                while True:
                    buffer = furl.read(block_sz)
                    if not buffer:
                        break
                    fout.write(buffer)

                fout.close()                            
            except Exception as e:
                raise Exception("Could not connect to server in URL");
            return_code = furl.getcode()
            if return_code != 200:
                raise Exception("Could not connect to query URL")

            print "Zip File saved to: " + zip_filename

    except Exception as e:
        print "ERROR: " + str(e)
    



if __name__ == '__main__':    

    try:
        if debug: print "Start"
        
        # Service URL
        server = r"http://egeoint.nrlssc.navy.mil/arcgis/rest/services/"
        gp_service_url = server + "gptools/mapServerTools/GPServer/exportMapServerQuery"

        # Create Params; Python dict for GP Service inputs
        if debug: print "Create Params"
        params = {}

        # Set the service you want to download
        params['inQueryURL'] = r"http://maps.stlouisco.com/ArcGIS/rest/services/Maps/Parcels/MapServer/0"

        # Create Parameters for Query
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        inParams['geometry'] = "-90.302,38.716,-90.289,38.721"
        inParams['inSR'] = 4326
        inParams['geometryType'] = "esriGeometryEnvelope"
        inParams['spatialRel'] = "esriSpatialRelIntersects"
        inParams['outSR'] = 4326
        # Turn the Python dict into JSON String
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson

        # Let's get a Shapefile
        params['inOutputFormat'] = "Shapefile"        
        

        # Submit the Job
        if debug: print "Submit Job"
        submitJob(gp_service_url, params)


    except:
        # Return any python specific errors as well as any errors from the geoprocessor
        #
        
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n    " + \
                str(sys.exc_type)+ ": " + str(sys.exc_value) + "\n"

        print pymsg

        msgs = "GP ERRORS:\n" + arcpy.GetMessages(2) + "\n"

        print msgs        
