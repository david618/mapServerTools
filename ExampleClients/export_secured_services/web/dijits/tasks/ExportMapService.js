dojo.provide("dijits.tasks.ExportMapService");


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

var debug = true;

var ExportMapService = {
    // _Templated dijit setup stuff
    templateString: dojo.cache("dijits.tasks.ExportMapService", "templates/exportMapServiceTemplate.html"),
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
    services: null,  
    exportMapServerServiceUrl: null,
    jobId: null,

    
    
    postMixInProperties: function()
    {
        // init the GP services
        this.exportMapServerServiceGP = new esri.tasks.Geoprocessor(this.exportMapServerServiceUrl);
        
    // create the drawing toolbar
    },
    
    postCreate: function()
    {        
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

            if (debug) console.log(service);
            // Destroy all of the checkBox dijits
            var check;
            for (var j = 0; j < service.checks.length; j++)
            {
                check = service.checks[j];

                check.check.destroy();
            }
            // Destroy the radio dijit
            service.radio.destroy();
            // Clear the Div
            dojo.empty(this.serviceListContainer);
        }
        this._serviceControls = [];
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
            dojo.hitch(this, this._exportMapService());
        });

        dojo.connect(this.map, "onLayerAdd", this, function(service)
        {
            dojo.hitch(this, this._addServiceToExportList(service));
        });

        dojo.connect(this.selectAllButton, "onClick", this, function(evt)
        {
            if (debug) console.log("Select All");
            for (var i = 0; i < this._serviceControls.length; i++)
            {
                service = this._serviceControls[i];
                if (service.radio.checked) {
                    console.log(service.name);
                    for (var j = 0; j < service.checks.length; j++)
                    {
                        checkData = service.checks[j];
                        check = checkData.check;
                        check.set("checked", true);
                    }                    
                }


            }
        });

        dojo.connect(this.unSelectAllButton, "onClick", this, function(evt)
        {
            if (debug) console.log("Select All");
            for (var i = 0; i < this._serviceControls.length; i++)
            {
                service = this._serviceControls[i];
                if (service.radio.checked) {
                    if (debug) console.log(service.name);
                    for (var j = 0; j < service.checks.length; j++)
                    {
                        checkData = service.checks[j];
                        check = checkData.check;
                        check.set("checked", false);
                    }
                }


            }
        });

        dojo.connect(this.setToMapButton, "onClick", this, function(evt)
        {
            if (debug) console.log("Set to Map");
            for (var i = 0; i < this._serviceControls.length; i++)
            {
                service = this._serviceControls[i];
                if (debug) console.log(service.name);
                if (debug) console.log(visibleLayers);
                if (service.radio.checked) {
                    visibleLayers = this.map.getLayer(service.name).visibleLayers;

                    for (var j = 0; j < service.checks.length; j++)
                    {
                        checkData = service.checks[j];
                        check = checkData.check;
                        value = checkData.check.value;
                        if (debug) console.log(value);

                        if (visibleLayers.indexOf(value) == -1) {
                            check.set("checked", false);
                        } else {
                            check.set("checked", true);
                        }

                    }
                }


            }
        });

        dojo.connect(this.cancelButton, "onClick", this, function(evt)
        {
            // Clear Export Service Message
            dojo.empty(this.serviceMessages);

            if (debug) console.log(this.jobId);
            if (this.jobId != null) {
                this.exportMapServerServiceGP.cancelJobStatusUpdates(this.jobId);
            }

            this.exportButton.cancel();

            if (debug) console.log(this._clippingPolyGraphic);


            if (this._clippingPolyGraphic != null) {
                var dialog = new dijit.Dialog({
                    title: 'Confirmation'
                });
                dojo.create('div', {
                    innerHTML: 'Do you want to remove the polygon?'
                }, dialog.containerNode /* the content portion of the dialog you're creating */);
                var div = dojo.create('div', {}, dialog.containerNode);

                var yes = new dijit.form.Button({
                    label: "Yes"
                }).placeAt(div,"last");

                dojo.connect(yes, "onClick", this, function(evt) {
                        if (debug) console.log("OK here");
                        this._clippingDrawToolbar.deactivate();
                        this._clearClippingGraphic();
                    dialog.hide();
                    dojo.destroy(dialog);
                });


                var no = new dijit.form.Button({
                    label: "No"
                }).placeAt(div,"last");

                dojo.connect(no, "onClick", this, function(evt) {
                    dialog.hide();
                    dojo.destroy(dialog);
                });

                dialog.show();
            }
        });

    },
    
    _showExportOptions: function(value)
    {
        switch (value)
        {
            case "map":
                
                // disable the draw poly button
                this.drawPolyButton.set("disabled", true);
                break;
            case "custom":
                
                // enable the draw poly button
                this.drawPolyButton.set("disabled", false);
                break;
            default:
                
                // disable the draw poly button
                this.drawPolyButton.set("disabled", true);
                break;
        }
    },

    _addServiceToExportList: function(service)
    {
        if (debug) console.log(service.id)
        if (debug) console.log(service.url)


        if (! (service==undefined)) {
            if (service._tileIds == undefined) {
                var serviceName = service.id;
                var serviceURL = service.url;

                // Create a div for the service
                var containerDiv = dojo.create("div", {
                    id: serviceName + "_container",
                    "class": "exportMapServiceServiceContainer"
                }, this.serviceListContainer, "last");

                // Create service radio button 
                var serviceRadio = new dijit.form.RadioButton({
                    type: "radio",
                    name: "serviceToExport",
                    value: serviceURL,
                    onChange: dojo.hitch(this, function(state)
                    {
                        this._toggleService(state, serviceRadio);
                    })
                }).placeAt(containerDiv);

                // Create label
                dojo.create("label", {
                    innerHTML: serviceName
                }, containerDiv, "last");

                // Add a break
                dojo.create("br", null, containerDiv, "last");

                // Create checkBox and label for each layer
                var layerName;
                var layerChecks = [];

                // Add LayerDiv to
                var layersDiv = dojo.create("div", {
                    id: serviceName + "_layers_container",
                    style:"display:none",
                    "class": "exportMapServiceLayersContainer"
                }, this.layerListContainer, "last");


                visibleLayers = service.visibleLayers;

                dojo.create("label", {
                    innerHTML: "Layers"
                }, layersDiv, "last");
                dojo.create("br", null, layersDiv, "last");


                // This is not a tiled map service
                dojo.forEach(service.layerInfos, function(layerInfo){
                    
                    if (debug) console.log(layerInfo);                  
                    layerId = layerInfo.id;
                    
                    layerVisible = true
                    if (visibleLayers.indexOf(layerId) == -1)
                        layerVisible = false
                    layerName = layerInfo.name;
                    var subLayerIds = layerInfo.subLayerIds;

                    if (subLayerIds == null) {
                        // If it's not null assume it's Group Layer skip
                        var layerCheck = new dijit.form.CheckBox({
                            type: "checkbox",
                            id: serviceName + "/" + layerName + "-CHK",
                            value: layerId.toString(),
                            disabled: true,
                            style: "margin-left:20px"
                        }).placeAt(layersDiv);

                        // Add the checkBox dijit to the checkBox list
                        layerChecks.push({
                            check: layerCheck,
                            checked: layerVisible
                        });
                    } 
                    dojo.create("label", {
                        "for": serviceName + "/" + layerId + "-CHK",
                        innerHTML: layerName
                    }, layersDiv, "last");
                    dojo.create("br", null, layersDiv, "last");



                })

                // Create the object containing the controls for this service and add
                // it to the master controls list
                var serviceControls = {
                    name: serviceName,
                    radio: serviceRadio,
                    checks: layerChecks
                };
                this._serviceControls.push(serviceControls);
            }
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

            layerdivid = service.name + "_layers_container";
            console.log(layerdivid);

            if (state) {
                // Make the div visiblle
                dojo.style(layerdivid,{
                    display: "inline"
                });
            } else {
                dojo.style(layerdivid,{
                    display: "none"
                });
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
    
    _exportMapService: function()
    {
        try {


            dojo.empty(this.serviceMessages);
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

            var queryParams = {
                "where":"1=1",
                "outFields":"*"
            };

            switch (formValues.clipPolyOption)
            {
                case "map":
                    var mapExtent = this.map.extent;
                    var mapExtentPoly = new esri.geometry.Polygon(this.map.spatialReference);
                    mapExtentPoly.addRing([[mapExtent.xmin, mapExtent.ymax], [mapExtent.xmax, mapExtent.ymax], [mapExtent.xmax, mapExtent.ymin], [mapExtent.xmin, mapExtent.ymin], [mapExtent.xmin, mapExtent.ymax]]);
                    if (debug) console.log("Extent:");
                    if (debug) console.log(dojo.toJson(mapExtent));
                    queryParams['geometry'] = mapExtent.xmin + "," + mapExtent.ymin + "," + mapExtent.xmax + "," + mapExtent.ymax;
                    queryParams['inSR'] = mapExtent.spatialReference.wkid;
                    queryParams['geometryType'] = "esriGeometryEnvelope";
                    queryParams['spatialRel'] = "esriSpatialRelIntersects"
                    break;
                case "custom":
                    if (this._clippingPolyGraphic == null) {
                        throw "For Custom Export you must draw a Polygon.";
                    }

                    graphic_poly = this._clippingPolyGraphic.geometry;
                    if (debug) console.log("Custom Poly:");
                    if (debug) console.log(dojo.toJson(graphic_poly));
                    rings = {
                        "rings":graphic_poly.rings
                    };
                    queryParams['geometry'] = rings;
                    queryParams['inSR'] = graphic_poly.spatialReference.wkid;
                    queryParams['geometryType'] = "esriGeometryPolygon";
                    queryParams['spatialRel'] = "esriSpatialRelIntersects"
                    break;
                default:
                    // Have to use a hardcoded string here.  This service will not work without a "features" attribute
                    // and a FeatureSet with no features will not pass an empty "features" list to the service.
                    break;
            }


            // Build the GP parameters
            var params = {
                "inMapServerURL": formValues.serviceName,
                "inLayers": formValues.layerNames,
                "inQueryParams": dojo.toJson(queryParams),
                "inOutputFormat": "Shapefile"
            };

            if (debug) console.log(dojo.toJson(params));

            // Fire off the GP job
            this.exportMapServerServiceGP.setUpdateDelay(5000);  // Set up check every 5 seconds
            this.exportMapServerServiceGP.submitJob(params, dojo.hitch(this, this._exportServiceComplete), this._exportServiceStatus, dojo.hitch(this, this._exportServiceError));
            

        } catch (err) {
            alert(err);
            this.exportButton.cancel();
        }
    },
    
    _getFormValues: function()
    {
        // Get the selected service
        var service, svcURL;
        var selectedLayers = [], selectedLayersStr;
        for (var i = 0; i < this._serviceControls.length; i++) 
        {
            service = this._serviceControls[i];
            if (service.radio.get("checked")) 
            {
                svcURL = service.radio.get("value");
                if (debug) console.log(service.radio.get("value"))
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
            "serviceName": svcURL,
            "layerNames": selectedLayersStr,
            "clipPolyOption": clipPolyOption
        };
        
        return retObj;
    },
    
    _exportServiceComplete: function(jobInfo)
    {
        jobId = null
        if (jobInfo.jobStatus == "esriJobFailed") 
        {
            alert("Job Failed!" );
        } else {
            // Success
            this.exportMapServerServiceGP.getResultData(jobInfo.jobId, "outZipFile", this._downloadFile, dojo.hitch(this, this._exportServiceError));
        }

        this._showMessages(jobInfo);
        
        //this._clearClippingGraphic();
        this.exportButton.cancel();
    },
    
    _exportServiceStatus: function(jobInfo)
    {
        this.jobId = jobInfo.jobId;
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
        
        alert("Export failed.\n" + err.message + detailsStr);
    },
    
    _downloadFile: function(theFile)
    {
        var fileUrl = theFile.value.url;
        if (debug) console.log("The URL for the zipped export is " + fileUrl);
        window.location = fileUrl;
    },

    _showMessages: function(jobInfo)
    {

        
        var messageList = dojo.create("ul", null, this.serviceMessages, "last");

        dojo.forEach(jobInfo.messages, function(message){
            if (debug) console.log(message.type + ": " + message.description);
            dojo.create("li", {
                innerHTML: message.type + ": " + message.description
            }, messageList, "last");
        });
        /*
       if (warnings != "") {
           alert(warnings);
       }
       */
    }
    
};

dojo.declare("dijits.tasks.ExportMapService", [dijit._Widget, dijit._Templated], ExportMapService);
