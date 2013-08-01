import arcpy, urllib, json

class Toolbox:
    def __init__(self):
        # Define the toolbox (the toolbox name is the name of the .pyt file)
        self.alias       = "REST Tools"
        self.name        = "RESTTools"
        self.label       = "REST Tools"
        self.description = "Tools for working with AGS REST endpoints"

        # List of tool classes associated with this toolbox
        self.tools = [RestHarvester]

class RestHarvester:
    def __init__(self):
        # Define the tool (tool name is the name of the class)
        self.name        = "RESTHarvester"
        self.alias       = "REST Harvester"
        self.label       = "REST Harvester"
        self.description = "Save an AGS rest layer endpoint as a featureclass"
        self.helpfile    = ""

    def getParameterInfo(self):
        # Define parameter definitions
        AGSLayerURL = arcpy.Parameter()
        AGSLayerURL.displayName   = "AGS REST layer URL"
        AGSLayerURL.name          = "inAGSURL"
        AGSLayerURL.datatype      = "String"
        AGSLayerURL.parameterType = "Required"
        AGSLayerURL.direction     = "Input"

        outFC = arcpy.Parameter()
        outFC.displayName   = "Output Workspace"
        outFC.name          = "outWorkSpace"
        outFC.datatype      = "Workspace"
        outFC.parameterType = "Required"
        outFC.direction     = "Input"

        outLayerName = arcpy.Parameter()
        outLayerName.displayName   = "Layer Name"
        outLayerName.name          = "LayerName"
        outLayerName.datatype      = "String"
        outLayerName.parameterType = "Required"
        outLayerName.direction     = "Input"        

        params = [AGSLayerURL, outFC, outLayerName]        
        return params

    def isLicensed(self):
        # This is used to return whether the tool is licensed to execute
        # Optional
        return True

    def updateParameters(self, parameters):
        # Updates parameters based on changes made on the tool's dialog box
        # Optional
        return

    def updateMessages(self, parameters):
        # Modify parameter messages
        # Optional
        return

    def execute(self, parameters, messages):
        # The source code of the tool
        def makeRow(feature, fields):
            row = []
            for field in fields:
                if field['name'] == 'SHAPE@XY':
                    row.append((feature['geometry']['x'], feature['geometry']['y']))
                elif field['type'] == 'DATE':
                    try:
                        t = feature['attributes'][field['name']] / 1000
                        row.append(datetime.date.fromtimestamp(t).strftime("%m/%d/%Y %I:%M:%S %p"))
                    except:
                        row.append(None)
                else:
                    row.append(feature['attributes'][field['name']])
            return row

                
        inAGSLayerURL = parameters[0].valueAsText
        outWorkSpace  = parameters[1].valueAsText
        outLayerName  = parameters[2].valueAsText

        arcpy.env.workspace = outWorkSpace
        #arcpy.env.scratchWorkspace = outWorkSpace
        arcpy.env.overwriteOutput = True
        
        messages.AddMessage('Getting Feature Count From: ' + inAGSLayerURL)
        args = {}
        args.update({
            'f':'json',
            'where':'1=1',
            'returnIdsOnly':'true'
        })
        url = inAGSLayerURL + '/query?' + urllib.urlencode(args)
        layerIds = json.load(urllib.urlopen(url))
        messages.AddMessage('Total number of Features: ' + str(len(layerIds['objectIds'])))
                                                               
        messages.AddMessage('Running First Query...')
        args = {}
        args.update({
            'f':'json',
            'where':'1=1',
            'outFields':'*',
            'returnGeometry':'true'
        })
        url = inAGSLayerURL + '/query?' + urllib.urlencode(args)
        layerFset = json.load(urllib.urlopen(url))
        messages.AddMessage('Layer Type: ' + layerFset['geometryType'])
        messages.AddMessage('Layer SR: ' + str(layerFset['spatialReference']['wkid']))
        
        fcSR = arcpy.SpatialReference()
        fcSR.factoryCode = layerFset['spatialReference']['wkid']
        fcSR.create()
        
        inFields = []
        for field in layerFset['fields']:
            if field['type'] == 'esriFieldTypeString':
                inFields.append({'name': field['name'], 'length': field['length'], 'type':'TEXT', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeDouble':
                inFields.append({'name': field['name'], 'length': 0, 'type':'DOUBLE', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeDate':
                inFields.append({'name': field['name'], 'length': field['length'], 'type':'DATE', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeSmallInteger':
                inFields.append({'name': field['name'], 'length': 0, 'type':'SHORT', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeInteger':
                inFields.append({'name': field['name'], 'length': 0, 'type':'LONG', 'alias':field['alias']})
            elif field['type'] == 'esriFieldTypeFloat':
                inFields.append({'name': field['name'], 'length': 0, 'type':'FLOAT', 'alias':field['alias']})
                
        messages.AddMessage(inFields)

        arcpy.CreateFeatureclass_management(arcpy.env.workspace, outLayerName, 'POINT', '#', 'DISABLED', 'DISABLED', fcSR)
        selFields = []
        for field in inFields:
            selFields.append(field['name'])
            arcpy.AddField_management(outLayerName, field['name'], field['type'], '#', '#', field['length'], field['alias'])

        selFields.append('SHAPE@XY')
        inFields.append({'name': 'SHAPE@XY','type':'geometry'})
        messages.AddMessage(selFields)
        
        iCur = arcpy.da.InsertCursor(outLayerName, selFields)
        rows = 0
        for feature in layerFset['features']:
            iCur.insertRow(makeRow(feature, inFields))
            rows +=1
        messages.AddMessage('Inserted ' + str(rows) + ' Rows')
        del iCur
        return
