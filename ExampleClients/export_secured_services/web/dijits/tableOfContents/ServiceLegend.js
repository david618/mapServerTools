dojo.provide("dijits.tableOfContents.ServiceLegend");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.form.CheckBox");
dojo.require("dojo.cache");
dojo.require("esri.layers.agsdynamic");
dojo.require("esri.layers.agstiled");
dojo.require("esri.layers.FeatureLayer");
dojo.require("dijits.ExtendFunctionality");

var ServiceLegend = {
    templateString: dojo.cache("dijits.tableOfContents.ServiceLegend", "templates/serviceLegendTemplate.html"),
    
    // Attributes
    mapLayer: null,
    serviceName: null,
    createdDijits: [],
    
    postMixInProperties: function()
    {
		if (!this.serviceName) 
        {
            var name = this.mapLayer.id.split("_").join(" ");
            this._set("serviceName", name);
        }
        
        this.legendShouldBeBuilt = true;
        if (this.mapLayer.declaredClass == "esri.layers.ArcGISTiledMapServiceLayer" ||
        this.mapLayer.declaredClass == "esri.layers.ArcGISImageServiceLayer") 
        {
            this.legendShouldBeBuilt = false;
        }
    },
    
    postCreate: function()
    {
        this.serviceLegendDiv.id = this.mapLayer.id + "-Legend";
        
        this._buildServiceElement();
        
        // Listen to see if the visibility of the service changes.  Reflect 
        // outside changes on the checkbox
        dojo.connect(this.mapLayer, "onVisibilityChange", this, function(visibility)
        {
            this.serviceCheckBox.set("checked", visibility);
        });
        
        if (this.legendShouldBeBuilt) 
        {
            this._retrieveAndBuildLegend();
        }
    },
    
    destroy: function()
    {
        this.serviceCheckBox.destroy();
        
        // Destroy any dijits that have been dynamically generated
        dojo.forEach(this.createdDijits, function(dijit)
        {
            dijit.destroy();
        });
    },
    
    getMapLayerId: function()
    {
        return this.mapLayer.id;
    },
    
    _retrieveAndBuildLegend: function()
    {
        var legendUrl = this._getLegendUrl();
        
        esri.request({
            url: legendUrl,
            content: {
                f: "json"
            },
            handleAs: "json",
            preventCache: true,
            callbackParamName: "callback",
            load: dojo.hitch(this, function(response, io)
            {
                this._buildLegendElements(response);
            }),
            error: dojo.hitch(this, function(error, io)
            {
              console.warn("Failed to retrieve legend for layer \"" + this.mapLayer.id + "\": " + error);
            })
        });
    },
    
    _getLegendUrl: function()
    {
        // Start off with the URL from the layer
        var mapSvcUrl = this.mapLayer.url;
        
        // Fix it if it is a FeatureService layer
        if (this.mapLayer.declaredClass == "esri.layers.FeatureLayer") 
        {
            // Make sure we are looking at a MapService URL
            if (this.mapLayer.url.indexOf("FeatureServer") != -1) 
            {
                mapSvcUrl = this.mapLayer.url.replace("FeatureServer", "MapServer");
            }
            // Drop the layer id from the URL
            mapSvcUrl = mapSvcUrl.slice(0, mapSvcUrl.lastIndexOf("/"));
        }
        
        return mapSvcUrl + "/legend";
    },
    
    _buildServiceElement: function()
    {
        this.svcName.innerHTML = this.serviceName;
        
        this.serviceCheckBox = new dijit.form.CheckBox({
            onClick: dojo.hitch(this, this._toggleMapService),
            checked: true,
            title: "Layer visible in map",
            "class": "checkBox"
        }, this.svcCheck);
        
        this.opacitySlider = new dijit.form.HorizontalSlider({
            name: "slider",
            value: this.mapLayer.opacity,
            minimum: 0,
            maximum: 1,
            showButtons: true,
            intermediateChanges: true,
            onChange: dojo.hitch(this, function(value)
            {
                this.mapLayer.setOpacity(value);
            })
        }, this.transparencySlider);
    },
    
    _buildLegendElements: function(response)
    {
        dojo.replaceClass(this.serviceElement, "serviceElement", "serviceElementOnly");
        if (this.mapLayer.declaredClass == "esri.layers.FeatureLayer") 
        {
            dojo.forEach(response.layers, dojo.hitch(this, function(layerInfo, i)
            {
                // Only build the legend for this layer, not the whole thing
                if (layerInfo.layerId == this.mapLayer.layerId) 
                {
                    this._buildFeatureElements(layerInfo);
                }
            }));
        }
        else 
        {
            dojo.forEach(response.layers, dojo.hitch(this, function(layerInfo, i)
            {
                // build the layer entry
                this._buildLayerElement(layerInfo);
                
                // build sub-layer entries if there are any
                if (layerInfo.legend.length > 1) 
                {
                    this._buildFeatureElements(layerInfo);
                }
            }));
        }
    },
    
    _buildLayerElement: function(layerInfo)
    {
        // Create the elements
        var row = dojo.create("tr", null, this.layers, "last");
        var chkTd = dojo.create("td", null, row, "last");
        var infoTd = dojo.create("td", null, row, "last");
        
        // Create the check box
        var layerChk = new dijit.form.CheckBox({
            id: this.mapLayer.id + "-" + layerInfo.layerId + "-CHK",
            onClick: dojo.hitch(this, this._toggleLayer),
            checked: (this.mapLayer.visibleLayers.indexOf(layerInfo.layerId) != -1),
            title: "Layer visible in Map",
            "class": "checkBox " + this.mapLayer.id + "-layerCheck"
        }).placeAt(chkTd);
        
        // Add to this.createdDijits for cleanup
        this.createdDijits.push(layerChk);
        
        // Create the image and label
        if (layerInfo.legend.length == 1 && this.mapLayer.declaredClass == "esri.layers.ArcGISDynamicMapServiceLayer") 
        {
            // There is only one feature type for this layer so we will use that
            // one image for the layer 
            dojo.create("div", {
                innerHTML: "<img style=\"vertical-align:middle;\" src='" + this.mapLayer.url + "/" + layerInfo.layerId + "/images/" + layerInfo.legend[0].url + "'/>&nbsp;" + layerInfo.layerName
            }, infoTd, "last");
        }
        else 
        {
            // There are no or multiple features for this layer.  Just display
            // the layer's name
            dojo.create("div", {
                innerHTML: layerInfo.layerName
            }, infoTd, "last");
        }
    },
    
    _buildFeatureElements: function(layerInfo)
    {
        var featureInfos = layerInfo.legend;
        
        var row, chkTd, infoTd, imgPath;
        var featureId, featureChk, featureLabel;
        dojo.forEach(featureInfos, dojo.hitch(this, function(featureInfo)
        {
            // Create the elements
            row = dojo.create("tr", null, this.layers, "last");
            chkTd = dojo.create("td", null, row, "last");
            infoTd = dojo.create("td", null, row, "last");
            
            // if featureLayer, create checkbox
            if (this.mapLayer.declaredClass == "esri.layers.FeatureLayer") 
            {
                featureId = this._getFeatureIdFromName(featureInfo.label);
                
                // Create the image path
                var mapSvcUrl = this.mapLayer.url.replace("FeatureServer", "MapServer");
                imgPath = mapSvcUrl + "/images/" + featureInfo.url;
                
                if (featureId != -1) 
                {
                    // Create the feature show/hide checkbox
                    featureChk = new dijit.form.CheckBox({
                        id: this.mapLayer.id + "-" + featureId + "-CHK",
                        onClick: dojo.hitch(this, this._toggleFeature),
                        checked: true,
                        title: "Layer visible in Map",
                        "class": "checkBox " + this.mapLayer.id + "-featureCheck"
                    }).placeAt(chkTd);
                    
                    // Add to this.createdDijits for cleanup
                    this.createdDijits.push(featureChk);
                }
            }
            else 
            {
                // Create the image path for normal layers
                imgPath = this.mapLayer.url + "/" + layerInfo.layerId + "/images/" + featureInfo.url;
            }
            
            featureLabel = this._cleanLabelString(featureInfo.label);
            
            dojo.create("div", {
                innerHTML: "<img style=\"vertical-align:middle;\" src=\"" + imgPath + "\"/>&nbsp;" + featureLabel
            }, infoTd, "last");
        }));
    },
    
    _getFeatureIdFromName: function(featureName)
    {
        var featureId = -1;
        for (var i = 0; i < this.mapLayer.types.length; i++) 
        {
            if (featureName == this.mapLayer.types[i].name) 
            {
                featureId = this.mapLayer.types[i].id;
            }
        }
        
        return featureId;
    },
    
    /**
     * gets rid of HTML control characters
     * @param {Object} labelStr
     */
    _cleanLabelString: function(labelStr)
    {
        var label = labelStr;
        label = label.replace("<", "");
        label = label.replace(">", "");
        
        return label;
    },
    
    _toggleMapService: function(evt)
    {
        if (this.serviceCheckBox.checked) 
        {
            this.mapLayer.show();
        }
        else 
        {
            this.mapLayer.hide();
        }
    },
    
    _toggleLayer: function(evt)
    {
        var id = evt.target.id.split("-")[0];
        var refLayers = dojo.query("." + this.mapLayer.id + "-layerCheck>");
        var visible = [];
        dojo.forEach(refLayers, function(layer)
        {
            if (layer.checked) 
            {
                visible.push(layer.id.split("-")[1]);
            }
        });
        if (visible.length > 0) 
        {
            this.mapLayer.setVisibility(this.serviceCheckBox.checked);
            this.mapLayer.setVisibleLayers(visible);
        }
        else 
        {
            this.mapLayer.hide();
        }
    },
    
    _toggleFeature: function(evt)
    {
        var featureId = evt.target.id.split("-")[1];
        var typeIdField = this.mapLayer.typeIdField;
        var defExp = this.mapLayer.getDefinitionExpression();
        var featureArray = [];
        var i = 0;
        
        if (!defExp) 
        {
            // Build up the definition expression if one does not exist.  All values are shown
            for (i = 0; i < this.mapLayer.types.length; i++) 
            {
                featureArray.push(i);
            }
        }
        else 
        {
            // Get the layerIds as an array from the definition expression
            featureArray = defExp.substring(defExp.indexOf("(") + 1, defExp.indexOf(")")).split(",");
        }
        
        if (evt.target.checked) 
        {
            // Add the feature to the visible list
            featureArray.push(featureId);
        }
        else 
        {
            // Remove this feature id from the definition query 
            var editedArray = [];
            for (i = 0; i < featureArray.length; i++) 
            {
                if (featureId != featureArray[i]) 
                {
                    editedArray.push(featureArray[i]);
                }
            }
            
            featureArray = editedArray;
        }
        
        defExp = typeIdField + " in (" + featureArray + ")";
        this.mapLayer.setDefinitionExpression(defExp);
    }
};

dojo.declare("dijits.tableOfContents.ServiceLegend", [dijit._Widget, dijit._Templated], ServiceLegend);

