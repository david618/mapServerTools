dojo.provide("dijits.tasks.ClipAndShip");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.form.CheckBox");
dojo.require("dijit.form.RadioButton");
dojo.require("dijit.layout.ContentPane");
dojo.require("dijit.layout.BorderContainer");
dojo.require("dijits.Utilities");
dojo.require("dojo.cache");
dojo.require("dojox.form.BusyButton");
dojo.require("esri.map");


var ClipAndShip = {
    // _Templated dijit setup stuff
    templateString: dojo.cache("dijits.tasks.ClipAndShip", "templates/clipAndShipTemplate.html"),
    widgetsInTemplate: true,
    
    // list of objects containing the radio button and check boxes relating to a specific service
    // this is used to easily find all controls associated with a service, and also for a handy way
    // to destroy all the controls "newed" during the life of this dijit
    // Object format is: {name: serviceName, radio: radioButtonDijit, checks: [{check: checkBox dijit, checked: persistent checked state}]}  
    _serviceControls: [],
    
    _clippingDrawToolbar: null,
    _clippingPolyGraphic: null,
    
    // Attributes
    map: null,
    services: null,  // Array of names of feature services to clip
    exportableLayersServiceUrl: null,
    exportServiceUrl: null,
    
    
    postMixInProperties: function()
    {
        // init the GP services
        this.getExportableLayersGP = new esri.tasks.Geoprocessor(this.exportableLayersServiceUrl);
        this.exportServiceGP = new esri.tasks.Geoprocessor(this.exportServiceUrl);
        
        // create the drawing toolbar
    },
    
    postCreate: function()
    {
        // Get the exportable services
        this._getExportableLayers();
        
        // initilize all the handlers
        this._initHandlers();
        
        // fire up the tool bar
        this._initToolbar();
    },
    
    destroy: function()
    {
        for (var i = 0; i < this._serviceControls.length; i++) 
        {
            service = this._serviceControls[i];
            
            // Destoroy the radio dijit
            service.radio.destroy();
            
            // Destory all of the checkBox dijits
            var check;
            for (var j = 0; j < service.checks.length; j++) 
            {
                check = service.checks[j];
                check.destroy();
            }
        }
    },
    
    _initToolbar: function()
    {
        // Create the toolbar and symbol for drawing the custom clipping poly
        this._clippingDrawToolbar = esri.toolbars.Draw(this.map, {
            showTooltips: true
        });
        
        dojo.connect(this._clippingDrawToolbar, "onDrawEnd", dojo.hitch(this, this._addClippingPoly));
    },
    
    _initHandlers: function()
    {
        dojo.connect(this.worldOptionRadio, "onClick", this, function(evt)
        {
            this._showExportOptions(evt.target.value);
        });
        dojo.connect(this.mapExtentOptionRadio, "onClick", this, function(evt)
        {
            this._showExportOptions(evt.target.value);
        });
        dojo.connect(this.customPolyOptionRadio, "onClick", this, function(evt)
        {
            this._showExportOptions(evt.target.value);
        });
        
        dojo.connect(this.drawPolyButton, "onClick", this, function(evt)
        {
            dojo.hitch(this, this._drawClippingPoly());
        });
        
        dojo.connect(this.exportButton, "onClick", this, function(evt)
        {
            dojo.hitch(this, this._clipAndShip());
        });
        
        dojo.connect(this.cancelButton, "onClick", this, function(evt)
        {
            this._clippingDrawToolbar.deactivate();
            this._clearClippingGraphic();
        });
    },
    
    _showExportOptions: function(value)
    {
        switch (value)
        {
            case "map":
                // enable the clipping check
                this.clipFeaturesCheck.set("disabled", false);
                
                // disable the draw poly button
                this.drawPolyButton.set("disabled", true);
                break;
            case "custom":
                // enable the clipping check
                this.clipFeaturesCheck.set("disabled", false);
                
                // enable the draw poly button
                this.drawPolyButton.set("disabled", false);
                break;
            default:
                // disable the clipping check
                this.clipFeaturesCheck.set("disabled", true);
                
                // disable the draw poly button
                this.drawPolyButton.set("disabled", true);
                break;
        }
    },
    
    _getExportableLayers: function()
    {
        var params = {};
        dojo.forEach(this.services, dojo.hitch(this, function(service)
        {
            params = {
                "ServiceName": service
            };
            
            this.getExportableLayersGP.submitJob(params, dojo.hitch(this, this._getExportLayersComplete), this._getExportLayersStatus, this._getExportLayersError);
        }));
    },
    
    _getExportLayersComplete: function(jobInfo)
    {
        if (jobInfo.jobStatus !== "esriJobFailed") 
        {
            this.getExportableLayersGP.getResultData(jobInfo.jobId, "LayerInfo", dojo.hitch(this, this._parseExportLayerInfo), this._getExportLayersError);
        }
    },
    
    _getExportLayersStatus: function(jobInfo)
    {
        console.info("Get Export Layers job: " + jobInfo.jobId + " status: " + jobInfo.jobStatus);
    },
    
    _getExportLayersError: function(err)
    {
        var detailsStr = "";
        if (err.details.length > 0) 
        {
            detailsStr = "\n - ";
            detailsStr += err.details.join("\n - ");
        }
        
        console.error("Get Export Layers failed: " + err.message + detailsStr);
    },
    
    _parseExportLayerInfo: function(result)
    {
        var layerInfoList = dojo.eval(result.value);
        
        if (layerInfoList.length > 0) 
        {
            var serviceName = layerInfoList[0].serviceName;
            
            var containerDiv = dojo.create("div", {
                id: serviceName + "_container",
                "class": "clipAndShipServiceContainer"
            }, this.serviceListContainer, "last");
            
            // Create service radio button and label
            var serviceRadio = new dijit.form.RadioButton({
                type: "radio",
                name: "serviceToExport",
                value: serviceName,
                onChange: dojo.hitch(this, function(state)
                {
                    this._toggleService(state, serviceRadio);
                })
            }).placeAt(containerDiv);
            dojo.create("label", {
                innerHTML: serviceName
            }, containerDiv, "last");
            dojo.create("br", null, containerDiv, "last");
            
            // Create checkBox and label for each layer
            var layerName;
            var layerChecks = [];
            dojo.forEach(layerInfoList, function(layerObj)
            {
                layerName = layerObj.layerName;
                var layerCheck = new dijit.form.CheckBox({
                    type: "checkbox",
                    //                    id: serviceName + "/" + layerName + "-CHK",
                    value: layerName,
                    checked: false,
                    disabled: true,
                    style: "margin-left:20px"
                }).placeAt(containerDiv);
                dojo.create("label", {
                    "for": serviceName + "/" + layerName + "-CHK",
                    innerHTML: layerName
                }, containerDiv, "last");
                dojo.create("br", null, containerDiv, "last");
                
                // Add the checkBox dijit to the checkBox list
                layerChecks.push({
                    check: layerCheck,
                    checked: true
                });
            });
            
            // Create the object containing the controls for this service and add 
            // it to the master controls list 
            var serviceControls = {
                name: serviceName,
                radio: serviceRadio,
                checks: layerChecks
            };
            this._serviceControls.push(serviceControls);
        }
    },
    
    _toggleService: function(state, serviceRadio)
    {
        var service;
        for (var i = 0; i < this._serviceControls.length; i++) 
        {
            service = this._serviceControls[i];
            if (service.radio !== serviceRadio) 
            {
                continue;
            }
            
            var check, checkData;
            for (var j = 0; j < service.checks.length; j++) 
            {
                checkData = service.checks[j];
                check = checkData.check;
                check.set("disabled", !state);
                if (state) 
                {
                    check.set("checked", checkData.checked);
                }
                else 
                {
                    checkData.checked = check.get("checked");
                    check.set("checked", false);
                }
            }
        }
    },
    
    _drawClippingPoly: function()
    {
        this._clearClippingGraphic();
        this._clippingDrawToolbar.activate(esri.toolbars.Draw.POLYGON);
    },
    
    _addClippingPoly: function(poly)
    {
        this._clippingDrawToolbar.deactivate();
        var symbol = new esri.symbol.SimpleFillSymbol(esri.symbol.SimpleFillSymbol.STYLE_SOLID, new esri.symbol.SimpleLineSymbol(esri.symbol.SimpleLineSymbol.STYLE_DASHDOT, new dojo.Color([255, 0, 0]), 2), new dojo.Color([255, 255, 0, 0.25]));
        this._clippingPolyGraphic = new esri.Graphic(poly, symbol);
        this.map.graphics.add(this._clippingPolyGraphic);
    },
    
    _clearClippingGraphic: function()
    {
        if (this._clippingPolyGraphic) 
        {
            this.map.graphics.remove(this._clippingPolyGraphic);
            this._clippingPolyGraphic = null;
        }
    },
    
    _clipAndShip: function()
    {
        // Get teh form imputs
        var formValues = this._getFormValues();
        
        // Make sure they filled out the required parts of the form
        if (!formValues.serviceName) 
        {
            console.warn("No service was selected for export");
            this.exportButton.set("label", "No Service Selected");
            setTimeout(dojo.hitch(this, function()
            {
                this.exportButton.cancel();
            }), 3000);
            return;
        }
        if (!formValues.layerNames) 
        {
            console.warn("No layers were selected for export");
            this.exportButton.set("label", "No Layers Selected");
            setTimeout(dojo.hitch(this, function()
            {
                this.exportButton.cancel();
            }), 3000);
            return;
        }
        
        // initialize the clipping feature set
        var clippingFeatureSet = new esri.tasks.FeatureSet();
        clippingFeatureSet.spatialReference = this.map.spatialReference;
        clippingFeatureSet.geometryType = "esriGeometryPolygon";
        
        switch (formValues.clipPolyOption)
        {
            case "map":
                var mapExtent = this.map.extent;
                var mapExtentPoly = new esri.geometry.Polygon(this.map.spatialReference);
                mapExtentPoly.addRing([[mapExtent.xmin, mapExtent.ymax], [mapExtent.xmax, mapExtent.ymax], [mapExtent.xmax, mapExtent.ymin], [mapExtent.xmin, mapExtent.ymin], [mapExtent.xmin, mapExtent.ymax]]);
                clippingFeatureSet.features.push(new esri.Graphic(mapExtentPoly));
                break;
            case "custom":
                clippingFeatureSet.features.push(this._clippingPolyGraphic);
                break;
            default:
                // Have to use a hardcoded string here.  This service will not work without a "features" attribute
                // and a FeatureSet with no features will not pass an empty "features" list to the service.
                clippingFeatureSet = '{"geometryType": "esriGeometryPolygon", "features": []}';
                break;
        }
        
        // Build the GP parameters
        var params = {
            "ServiceName": formValues.serviceName,
            "LayerNames": formValues.layerNames,
            "Polygon": clippingFeatureSet,
            "Clip": formValues.clipFlag,
            "Where": ""
        };
        
        // Fire off the GP job
        this.exportServiceGP.submitJob(params, dojo.hitch(this, this._exportServiceComplete), this._exportServiceStatus, dojo.hitch(this, this._exportServiceError));
        //this.exportButton.cancel();
    },
    
    _getFormValues: function()
    {
        // Get the selected service
        var service, svcName;
        var selectedLayers = [], selectedLayersStr;
        for (var i = 0; i < this._serviceControls.length; i++) 
        {
            service = this._serviceControls[i];
            if (service.radio.get("checked")) 
            {
                svcName = service.name;
                break;
            }
            
            service = null;
        }
        
        // If a service was selected, get the checked layers
        if (service) 
        {
            var check, checkData;
            for (var j = 0; j < service.checks.length; j++) 
            {
                checkDijit = service.checks[j].check;
                if (checkDijit.get("checked")) 
                {
                    selectedLayers.push(checkDijit.get("value"));
                }
            }
            
            selectedLayersStr = selectedLayers.join(", ");
        }
        
        // Get the type of clipping polygon we will use
        var clipPolyOption;
        if (this.worldOptionRadio.get("checked")) 
        {
            clipPolyOption = this.worldOptionRadio.get("value");
        }
        else if (this.mapExtentOptionRadio.get("checked")) 
        {
            clipPolyOption = this.mapExtentOptionRadio.get("value");
        }
        else if (this.customPolyOptionRadio.get("checked")) 
        {
            clipPolyOption = this.customPolyOptionRadio.get("value");
        }
        
        // Build and return the return values object
        var retObj = {
            "serviceName": svcName,
            "layerNames": selectedLayersStr,
            "clipPolyOption": clipPolyOption,
            "clipFlag": this.clipFeaturesCheck.checked
        };
        
        return retObj;
    },
    
    _exportServiceComplete: function(jobInfo)
    {
        if (jobInfo.jobStatus !== "esriJobFailed") 
        {
            this.exportServiceGP.getResultData(jobInfo.jobId, "Shapefile", this._downloadFile, dojo.hitch(this, this._exportServiceError));
        }
        
        this._clearClippingGraphic();
        this.exportButton.cancel();
    },
    
    _exportServiceStatus: function(jobInfo)
    {
        console.info("Export Sevice job: " + jobInfo.jobId + " status: " + jobInfo.jobStatus);
    },
    
    _exportServiceError: function(err)
    {
        var detailsStr = "";
        if (err.details.length > 0) 
        {
            detailsStr = "\n - ";
            detailsStr += err.details.join("\n - ");
        }
        console.error("Export Sevice failed: " + err.message + detailsStr);
        
        this.exportButton.cancel();
        
        alert("Clip and Ship failed.\n" + err.message + detailsStr);
    },
    
    _downloadFile: function(theFile)
    {
        var fileUrl = theFile.value.url;
        console.log("The URL for the zipped shapefile is " + fileUrl);
        window.location = fileUrl;
    }
    
};

dojo.declare("dijits.tasks.ClipAndShip", [dijit._Widget, dijit._Templated], ClipAndShip);
