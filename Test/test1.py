import arcpy,sys,traceback
import urllib,json,datetime
import os
from time import strftime, localtime
import time

debug = True

output_folder = r"C:\Temp"

testresultsfile = os.path.join(output_folder,"results.dat")

foutresults = None

check_interval_secs = 10

def log_message(msg, level="message", flog=foutresults):
    try:
        level = level.strip().lower()
        if level == "message":
            arcpy.AddMessage(msg)
        elif level == "warn":
            arcpy.AddWarning(msg)
        elif level == "error":
            arcpy.AddError(msg)
        else:
            # If level isn't a valid value AddMessage
            arcpy.AddMessage(msg)

        if flog:
            # Write message to file
            flog.write(msg + "\n")
            flog.flush()
        else:
            # Print message to screen
            print msg
    except Exception as e:
        print e
        


def submitJob(params, testname, service_url):

    
    flog = None
    try:

        zip_filename = os.path.join(output_folder, testname + ".zip")
        log_filename = os.path.join(output_folder, testname + ".log")
        flog = open(log_filename, "w")
        # Add the json output parameter
        params['f'] = "json"
        url_params = urllib.urlencode(params)
        
        query_url = service_url + "/submitJob?" + url_params
        
        if debug: log_message("query_url: " + query_url, flog=flog)
        
        furl = None
        try:
            furl = urllib.urlopen(query_url)
        except Exception as e:
            raise Exception("Could not connect to server in URL");
        return_code = furl.getcode()
        if debug: log_message("return code: " + str(return_code), flog=flog)
        if return_code != 200:
            raise Exception("Could not connect to query URL")
        resp = json.load(furl)

        if debug: log_message("resp: " + str(resp), flog=flog)

        jobStatus = None
        jobId = None
        try:
            jobStatus = resp['jobStatus']
            jobId = resp['jobId']
        except:
            # Error was returned from the server
            raise Exception("Failed to submit job")

        start_time = time.time()

        query_url = service_url + "/jobs/" + jobId + "?f=json"
        if debug: log_message("query_url: " + query_url, flog=flog)

        
        while jobStatus != "esriJobSucceeded" and jobStatus != "esriJobFailed":
            time.sleep(check_interval_secs)          
            furl = None
            try:
                furl = urllib.urlopen(query_url)
            except Exception as e:
                raise Exception("Could not connect to server in URL");
            return_code = furl.getcode()
            if debug: log_message("return code: " + str(return_code), flog=flog)
            if return_code != 200:
                raise Exception("Could not connect to query URL")
            resp = json.load(furl)

            #if debug: log_message("resp: " + str(resp), flog=flog)

            try:
                error = resp['error']
                # Error was returned from the server
                raise Exception("Failed to submit job")
            except:
                if debug: log_message("ok", flog=flog)

            try:
                jobStatus = resp['jobStatus']

                last_msg = resp['messages'][-1]
                elapsed_time = str(int(round(time.time() - start_time)))
                if debug: log_message(elapsed_time + ":" + str(last_msg))
                if debug: log_message(elapsed_time, flog=flog) 
                
                
            except:
                # Error was returned from the server
                raise Exception("Failed to submit job")

        log_message("Export took " + str(time.time() - start_time) + " seconds", flog=flog)
        log_message("Export took " + str(time.time() - start_time) + " seconds")

        msgs = resp['messages']
        log_message("Messages", flog=flog)
        for msg in msgs:
            log_message(str(msg), flog=flog)

        log_message("Test: " + testname)
        log_message(resp['messages'][-1]['description'], flog=foutresults)
        log_message(resp['messages'][-2]['description'], flog=foutresults)

            
        if jobStatus == "esriJobSucceeded":
            paramUrl = resp['results']['outZipFile']['paramUrl']

            # Query to retrieve the zip file path
            query_url = service_url + "/jobs/" + jobId + "/" + paramUrl + "?f=json"
            if debug: log_message("query_url: " + query_url, flog=flog)
            
            furl = None
            try:
                furl = urllib.urlopen(query_url)
            except Exception as e:
                raise Exception("Could not connect to server in URL");
            return_code = furl.getcode()
            if debug: log_message("return code: " + str(return_code), flog=flog)
            if return_code != 200:
                raise Exception("Could not connect to query URL")
            resp = json.load(furl)

            if debug: log_message("resp: " + str(resp), flog=flog)

            # Give the server a few seconds to get the output in place
            time.sleep(check_interval_secs)

            query_url = resp['value']['url']
            if debug: log_message("query_url: " + query_url, flog=flog)

            furl = None
            try:
                furl = urllib.urlopen(query_url)
                fout = open(zip_filename, 'wb')
                
                #meta = furl.info()
                #file_size = int(meta.getheaders("Content-Length")[0])
                #print "Downloading: %s Bytes: %s" % (zip_filename, file_size)

                #file_size_dl = 0
                block_sz = 8192
                while True:
                    buffer = furl.read(block_sz)
                    if not buffer:
                        break

                    #file_size_dl += len(buffer)
                    fout.write(buffer)
                    #status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                    #print status

                fout.close()

                filesize = os.path.getsize(zip_filename)
                log_message("ZipFile size: " + str(filesize))
                log_message("ZipFile size: " + str(filesize), flog=foutresults)
            
                
            except Exception as e:
                raise Exception("Could not connect to server in URL");
            return_code = furl.getcode()
            if debug: log_message("return code: " + str(return_code), flog=flog)
            if return_code != 200:
                raise Exception("Could not connect to query URL")
    except Exception as e:
        if debug: log_message("ERROR: " + str(e), flog=flog)
    finally:
        if flog:
            flog.close()
    




if __name__ == '__main__':    

    test_cases = []
    runtests = range(0,31)
    
    #runtests = [30]
    #runtests = range(1,13)
    #runtests.append(14)


    #server = r"http://localhost:8399/arcgis/rest/services/gptools/mapServerTools/GPServer/"
    server = r"http://egeoint.nrlssc.navy.mil/arcgis/rest/services/gptools/mapServerTools/GPServer/"
    
    if 0 in runtests:
        # Local test
        test_case = {}    
        test_case['testname'] = r"t0"    
        params = {}
        params['inMapServerURL'] = r"http://servicesbeta2.esri.com/arcgis/rest/services/MontgomeryQuarters/MapServer"
        params['inLayers'] = "1"
        test_case['params'] = params
        test_cases.append(test_case)

    if 1 in runtests:
        # Export Country    
        test_case = {}    
        test_case['testname'] = r"t1"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcgis/rest/services/overlays/AdminBorders/MapServer"
        params['inLayers'] = "7"
        test_case['params'] = params
        test_cases.append(test_case)

    if 2 in runtests:
        # SHAPE.AREA and SHAPE.LEN
        test_case = {}    
        test_case['testname'] = r"t2"    
        params = {}
        params['inMapServerURL'] = r"http://psstl.esri.com/ArcGIS/rest/services/PACM/HG/MapServer"
        params['inOutputFormat'] = r"Shapefile"
        params['inLayers'] = "0"
        params['inOutputFormat'] = r"Shapefile"
        test_case['params'] = params
        test_cases.append(test_case)


    if 3 in runtests:
        # ST_AREA and ST_LENGTH
        test_case = {}    
        test_case['testname'] = r"t3"    
        params = {}
        params['inMapServerURL'] = r"http://rmgsc.cr.usgs.gov/ArcGIS/rest/services/nhss_weat/MapServer"
        params['inLayers'] = "0"
        params['inOutputFormat'] = r"PersonalGeoDatabase"
        test_case['params'] = params
        test_cases.append(test_case)
    

    if 4 in runtests:
        # Export ALL
        test_case = {}    
        test_case['testname'] = r"t4"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/NTAD2011/MapServer"
        params['inLayers'] = "0"        
        params['inOutputFormat'] = r"Shapefile"
        params['inQueryParams'] = r'{"exportAll":"True"}'
        test_case['params'] = params
        test_cases.append(test_case)


    if 5 in runtests:
        # Shapefile with ID Field
        test_case = {}    
        test_case['testname'] = r"t5"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/NTAD2011/MapServer"
        params['inLayers'] = "18"                
        params['inOutputFormat'] = r"Shapefile"
        test_case['params'] = params
        test_cases.append(test_case)

    if 6 in runtests:
        # Shape_Leng and Shape_Length fields
        test_case = {}    
        test_case['testname'] = r"t6"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/NTAD2011/MapServer"
        params['inLayers'] = "31"                
        test_case['params'] = params
        test_cases.append(test_case)

    if 7 in runtests:
        # Shape_Leng and Shape_Length fields
        test_case = {}    
        test_case['testname'] = r"t7"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/locationlookup/MapServer"
        params['inLayers'] = "1"                
        inParams = {}
        inParams['exportAll'] = "True"
        inParams['where'] = "country_code = 'US'"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)

    if 8 in runtests:
        # ArcGIS 10.1 
        test_case = {}    
        test_case['testname'] = r"t8"    
        params = {}
        params['inMapServerURL'] = r"http://servicesbeta2.esri.com/arcgis/rest/services/MontgomeryQuarters/MapServer"
        params['inLayers'] = "0"                
        inParams = {}
        inParams['exportAll'] = "True"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)

    if 9 in runtests:
        # ArcGIS 10.1 
        test_case = {}    
        test_case['testname'] = r"t9"    
        params = {}
        params['inMapServerURL'] = r"http://servicesbeta2.esri.com/arcgis/rest/services/MontgomeryQuarters/MapServer"
        params['inLayers'] = "1"                
        inParams = {}
        inParams['exportAll'] = "True"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)


    if 10 in runtests:
        # ArcGIS 9.3
        test_case = {}    
        test_case['testname'] = r"t10"    
        params = {}
        params['inMapServerURL'] = r"http://maps.mygrcity.us/ArcGIS/rest/services/California/MapServer"
        params['inLayers'] = "0"        
        inParams = {}
        inParams['exportAll'] = "True"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)


    if 11 in runtests:
        # ArcGIS 9.3 with spatial query
        test_case = {}    
        test_case['testname'] = r"t11"    
        params = {}
        params['inMapServerURL'] = r"http://maps.stlouisco.com/ArcGIS/rest/services/Maps/Parcels/MapServer"
        params['inLayers'] = "0"                
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        inParams['geometry'] = "878095,1050101,878781,1050468"
        inParams['geometryType'] = "esriGeometryEnvelope"
        inParams['spatialRel'] = "esriSpatialRelIntersects"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)

    if 12 in runtests:
        # ArcGIS 9.3 with spatial query 4326 in and out
        test_case = {}    
        test_case['testname'] = r"t12"    
        params = {}
        params['inMapServerURL'] = r"http://maps.stlouisco.com/ArcGIS/rest/services/Maps/Parcels/MapServer"
        params['inLayers'] = "0"                
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        inParams['geometry'] = "-90.302,38.716,-90.289,38.721"
        inParams['inSR'] = 4326
        inParams['geometryType'] = "esriGeometryEnvelope"
        inParams['spatialRel'] = "esriSpatialRelIntersects"
        inParams['outSR'] = 4326
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)


    if 13 in runtests:
        # Export Service local
        test_case = {}    
        test_case['testname'] = r"t13"    
        params = {}
        params['inMapServerURL'] = r"http://web2.nbmg.unr.edu/ArcGIS/rest/services/WA_data/WABoreholeObservations/MapServer"
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)
    
    if 14 in runtests:
        # Export Service local
        test_case = {}    
        test_case['testname'] = r"t14"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/locationlookup/MapServer"
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        inParams['geometry'] = "-80,34,-74,38"
        inParams['geometryType'] = "esriGeometryEnvelope"
        inParams['spatialRel'] = "esriSpatialRelIntersects"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)

    if 15 in runtests:
        # Export Service local
        test_case = {}    
        test_case['testname'] = r"t15"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcgis/rest/services/overlays/AdminBorders/MapServer"
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "CITY_NAME"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        params['inLayers'] = "14"
        test_case['params'] = params
        test_cases.append(test_case)        


    if 16 in runtests:
        # Export Service local
        test_case = {}    
        test_case['testname'] = r"t16"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcgis/rest/services/overlays/AdminBorders/MapServer"
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "CITY_NAME2"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        params['inLayers'] = "14"
        test_case['params'] = params
        test_cases.append(test_case)  

    if 17 in runtests:
        test_case = {}    
        test_case['testname'] = r"t17"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/locationlookup/MapServer"
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        inParams['geometry'] = '{"rings":[[[-10124008.08980318,4710187.298721861],[-10108873.55820271,4719206.868059516],\
                [-10085025.205377726,4721805.727021213],[-10065915.948306425,4719665.490229227],[-10049252.67614025,4710798.794948143],\
                [-10040844.603028877,4700250.485044785],[-10035188.262935773,4687409.06429287],[-10060871.104439601,4667535.436938717],\
                [-10069126.303494403,4676096.384106659],[-10068361.933211552,4697193.0039133765],[-10082426.346416028,4706059.69919446],\
                [-10092057.411979964,4710187.298721861],[-10101994.225657042,4699944.736931643],[-10090681.54547083,4683434.33882204],\
                [-10112695.40961697,4675790.635993519],[-10128135.689330582,4693676.9006122565],[-10124008.08980318,4710187.298721861]]]}'
        inParams['inSR'] = 102100
        inParams['geometryType'] = "esriGeometryPolygon"
        inParams['spatialRel'] = "esriSpatialRelIntersects"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)


    if 18 in runtests:
        test_case = {}    
        test_case['testname'] = r"t18"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/locationlookup/MapServer"
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        geometry = {}
        geometry['rings'] = [[[-10124008.08980318,4710187.298721861],[-10108873.55820271,4719206.868059516],\
                [-10085025.205377726,4721805.727021213],[-10065915.948306425,4719665.490229227],[-10049252.67614025,4710798.794948143],\
                [-10040844.603028877,4700250.485044785],[-10035188.262935773,4687409.06429287],[-10060871.104439601,4667535.436938717],\
                [-10069126.303494403,4676096.384106659],[-10068361.933211552,4697193.0039133765],[-10082426.346416028,4706059.69919446],\
                [-10092057.411979964,4710187.298721861],[-10101994.225657042,4699944.736931643],[-10090681.54547083,4683434.33882204],\
                [-10112695.40961697,4675790.635993519],[-10128135.689330582,4693676.9006122565],[-10124008.08980318,4710187.298721861]]]
        inParams['geometry'] = geometry
        inParams['inSR'] = 102100
        inParams['geometryType'] = "esriGeometryPolygon"
        inParams['spatialRel'] = "esriSpatialRelIntersects"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)


    if 19 in runtests:
        test_case = {}    
        test_case['testname'] = r"t19"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/locationlookup/MapServer"
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        geometry = {}
        geometry['rings'] = [[[-10124008.08980318,4710187.298721861],[-10108873.55820271,4719206.868059516],\
                [-10085025.205377726,4721805.727021213],[-10065915.948306425,4719665.490229227],[-10049252.67614025,4710798.794948143],\
                [-10040844.603028877,4700250.485044785],[-10035188.262935773,4687409.06429287],[-10060871.104439601,4667535.436938717],\
                [-10069126.303494403,4676096.384106659],[-10068361.933211552,4697193.0039133765],[-10082426.346416028,4706059.69919446],\
                [-10092057.411979964,4710187.298721861],[-10101994.225657042,4699944.736931643],[-10090681.54547083,4683434.33882204],\
                [-10112695.40961697,4675790.635993519],[-10128135.689330582,4693676.9006122565],[-10124008.08980318,4710187.298721861]]]
        inParams['geometry'] = geometry
        inParams['inSR'] = 102100
        inParams['geometryType'] = "esriGeometryPolygon"
        inParams['spatialRel'] = "esriSpatialRelIntersects"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        test_case['params'] = params
        test_cases.append(test_case)


    if 20 in runtests:
        test_case = {}    
        test_case['testname'] = r"t20"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcgis/rest/services/esri/gaz/MapServer"
        test_case['params'] = params
        test_cases.append(test_case)


    if 21 in runtests:
        test_case = {}    
        test_case['testname'] = r"t21"    
        params = {}
        params['inMapServerURL'] = r"http://mapserver.borough.kenai.ak.us/ArcGIS/rest/services/CodeEnforcement/ParcelPublicAccess/MapServer"
        params['inLayers'] = "95-107"
        test_case['params'] = params
        test_cases.append(test_case)  

    if 22 in runtests:
        test_case = {}    
        test_case['testname'] = r"t22"    
        params = {}
        params['inMapServerURL'] = r"http://mapserver.borough.kenai.ak.us/ArcGIS/rest/services/CodeEnforcement/ParcelPublicAccess/MapServer"
        params['inLayers'] = "95-107"
        test_case['params'] = params
        test_cases.append(test_case)  


    if 23 in runtests:
        test_case = {}    
        test_case['testname'] = r"t23"    
        params = {}
        params['inMapServerURL'] = r"http://gis.hicentral.com/arcgis/rest/services/OperEnv/MapServer"
        params['inLayers'] = "0,6"
        test_case['params'] = params
        test_cases.append(test_case)  

    if 24 in runtests:
        # Group Layers
        test_case = {}    
        test_case['testname'] = r"t24"    
        params = {}
        params['inMapServerURL'] = r"http://basemap.nationalmap.gov/ArcGIS/rest/services/TNM_Vector_Small/MapServer"
        params['inLayers'] = "8-12"
        test_case['params'] = params
        test_cases.append(test_case)  

    if 25 in runtests:        
        # Services accessed via a proxy
        test_case = {}    
        test_case['testname'] = r"t25"    
        params = {}
        params['inMapServerURL'] = r"http://monroeil.mygisonline.com/proxy.php?/ArcGIS/rest/services/MonroeIL/MapServer"
        params['inLayers'] = "4"
        test_case['params'] = params
        test_cases.append(test_case)  

    if 26 in runtests:
        # Layer from 9.3.1 has a field SHAPE_LEN
        test_case = {}    
        test_case['testname'] = r"t26"    
        params = {}
        params['inMapServerURL'] = r"http://maps.stlouisco.com/ArcGIS/rest/services/dw/AGS_Repository/MapServer"
        params['inLayers'] = "10"
        test_case['params'] = params
        test_cases.append(test_case)  


    if 27 in runtests:
        # Layer starts with digit
        test_case = {}    
        test_case['testname'] = r"t27"    
        params = {}
        params['inMapServerURL'] = r"http://services.nationalmap.gov/ArcGIS/rest/services/map_indices/MapServer"
        params['inLayers'] = "3"
        test_case['params'] = params
        test_cases.append(test_case)  


    if 28 in runtests:
        # Null Geometry returned as points with NaN
        test_case = {}    
        test_case['testname'] = r"t28"    
        params = {}
        params['inMapServerURL'] = r"http://naip.giscenter.isu.edu/ArcGIS/rest/services/ITD_STIP1/MapServer"
        params['inLayers'] = "1"
        test_case['params'] = params
        test_cases.append(test_case)

    if 29 in runtests:
        test_case = {}    
        test_case['testname'] = r"t29"    
        params = {}
        params['inMapServerURL'] = r"http://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places_Alternate/MapServer"
        test_case['params'] = params
        test_cases.append(test_case)


    if 30 in runtests:
        # Test clip
        test_case = {}    
        test_case['testname'] = r"t30"    
        params = {}
        params['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcgis/rest/services/overlays/AdminBorders/MapServer"
        inParams = {}
        inParams['where'] = "1=1"
        inParams['outFields'] = "*"
        inParams['geometry'] = '{"rings":[[[-10124008.08980318,4710187.298721861],[-10108873.55820271,4719206.868059516],\
                [-10085025.205377726,4721805.727021213],[-10065915.948306425,4719665.490229227],[-10049252.67614025,4710798.794948143],\
                [-10040844.603028877,4700250.485044785],[-10035188.262935773,4687409.06429287],[-10060871.104439601,4667535.436938717],\
                [-10069126.303494403,4676096.384106659],[-10068361.933211552,4697193.0039133765],[-10082426.346416028,4706059.69919446],\
                [-10092057.411979964,4710187.298721861],[-10101994.225657042,4699944.736931643],[-10090681.54547083,4683434.33882204],\
                [-10112695.40961697,4675790.635993519],[-10128135.689330582,4693676.9006122565],[-10124008.08980318,4710187.298721861]]]}'
        inParams['inSR'] = 102100
        inParams['geometryType'] = "esriGeometryPolygon"
        inParams['spatialRel'] = "esriSpatialRelIntersects"
        inParamsJson = json.dumps(inParams)
        params['inQueryParams'] = inParamsJson
        params['inLayers'] = "1"
        params['inClip'] = True
        test_case['params'] = params
        test_cases.append(test_case)
        
    '''    
a = '{"where":"1=1","outFields":"*","geometry":{"rings": [[[-10124008.08980318, 4710187.2987218611], [-10108873.55820271, 4719206.868059516], [-10085025.205377726, 4721805.7270212127], [-10065915.948306425, 4719665.4902292266], [-10049252.676140251, 4710798.794948143], [-10040844.603028877, 4700250.4850447848], [-10035188.262935773, 4687409.0642928705], [-10060871.104439601, 4667535.436938717], [-10069126.303494403, 4676096.3841066593], [-10068361.933211552, 4697193.0039133765], [-10082426.346416028, 4706059.6991944602], [-10092057.411979964, 4710187.2987218611], [-10101994.225657042, 4699944.7369316434], [-10090681.54547083, 4683434.3388220398], [-10112695.40961697, 4675790.6359935189], [-10128135.689330582, 4693676.9006122565], [-10124008.08980318, 4710187.2987218611]]]}}'

t = '{"where":"1=1","outFields":"*","geometry":{"rings":[[[-10068667.681324707,4693447.589527397],[-10036564.12944495,4685498.1385857435],[-10062552.719061896,4676631.443304667],[-10068667.681324707,4693447.589527397]]]},"inSR":102100,"geometryType":"esriGeometryPolygon","spatialRel":"esriSpatialRelIntersects"}'
    '''



    try:
        # Submit Job

        foutresults = open(testresultsfile, "w")

        service_url = server + "exportMapServerService"

        for test_case in test_cases:
            f = {}
            testname = test_case['testname']
            params = test_case['params']

            log_message("Working: " + testname)
            log_message("Working: " + testname, flog=foutresults)

            submitJob(params, testname, service_url)


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
            log_message(msgs, "error")
        else:
            log_message(str(sys.exc_value), "error")

    finally:
        foutresults.close()
