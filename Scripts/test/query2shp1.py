from urlparse import urlparse
from urllib2 import Request, urlopen
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

        p = urlparse(query_url + params)
        print p

        req = Request(query_url)

        f = urlopen(req)

        respJSON = "";

        a = f.read(4096)
        while (len(a) > 0):
            respJSON += a
            a = f.read(4096)

        f.close()

        resp = json.loads(respJSON)

        displayFieldName = resp['displayFieldName']
        fieldAliases = resp['fieldAliases']
        geometryType = resp['geometryType']
        spatialReference = resp['spatialReference']
        fields = resp['fields']
        features =  resp['features']

        for field in fields:
            print field['name'] + " : " + field['type'] + " : " + field['alias']
            

    except Exception as e:
        print e

    

