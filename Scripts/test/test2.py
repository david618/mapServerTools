import arcpy
import json
'''
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


params2 = {}
params2['inMapServerURL'] = r"http://egeoint.nrlssc.navy.mil/arcnga/rest/services/vector/locationlookup/MapServer"
inParams2 = {}
inParams2['where'] = "1=1"
inParams2['outFields'] = "*"
geom2 = {}
geom2['rings'] = [[[-10124008.08980318,4710187.298721861],[-10108873.55820271,4719206.868059516],\
        [-10085025.205377726,4721805.727021213],[-10065915.948306425,4719665.490229227],[-10049252.67614025,4710798.794948143],\
        [-10040844.603028877,4700250.485044785],[-10035188.262935773,4687409.06429287],[-10060871.104439601,4667535.436938717],\
        [-10069126.303494403,4676096.384106659],[-10068361.933211552,4697193.0039133765],[-10082426.346416028,4706059.69919446],\
        [-10092057.411979964,4710187.298721861],[-10101994.225657042,4699944.736931643],[-10090681.54547083,4683434.33882204],\
        [-10112695.40961697,4675790.635993519],[-10128135.689330582,4693676.9006122565],[-10124008.08980318,4710187.298721861]]]
inParams2['geometry'] = geom2
inParams2['inSR'] = 102100
inParams2['geometryType'] = "esriGeometryPolygon"
inParams2['spatialRel'] = "esriSpatialRelIntersects"
inParamsJson2 = json.dumps(inParams2)
params2['inQueryParams'] = inParamsJson2
'''


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


if __name__ == '__main__':
    t = '{"where":"1=1","outFields":"*","geometry":{"rings":[[[-10068667.681324707,4693447.589527397],[-10036564.12944495,4685498.1385857435],[-10062552.719061896,4676631.443304667],[-10068667.681324707,4693447.589527397]]]},"inSR":102100,"geometryType":"esriGeometryPolygon","spatialRel":"esriSpatialRelIntersects"}'

    obj = json.loads(t, object_hook=_decode_dict)
    
