dojo.provide("dijits.tableOfContents.TableOfContents");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dojo.cache");
dojo.require("dijits.tableOfContents.ServiceLegend");
dojo.require("dijits.ExtendFunctionality");

var TableOfContents = {
    templateString: dojo.cache("dijits.tableOfContents.TableOfContents", "templates/tocTemplate.html"),
    
    // Attributes
    map: null,
    priorityList: [],
    
    postMixInProperties: function()
    {
        // Listen for a layer to be removed
		dojo.connect(this.map, "onLayerRemove", this, this._onLayerRemoved);
    },
    
    /**
     * public method to add layer and optional layer name
     * 
     * @param {Object} layer
     * @param {Object} name
     */
	addLayer: function(layer, name)
    {
        // Create the new legend widget
        var legend = new dijits.tableOfContents.ServiceLegend({
            mapLayer: layer,
            serviceName: name
        });
        
        // Place the new legend in the DOM according to the priorityList
        var idx = this.priorityList.indexOf(layer.id);
        switch (idx)
        {
            case -1:
                // Layer is not in the priority list, so place at end
                dojo.place(legend.domNode, this.tocContent, "last");
                break;
            case 0:
                // Layer is first in priority list, so place at top
                dojo.place(legend.domNode, this.tocContent, "first");
                break;
            default:
                // Layer is on priority list, but not first
                var i = 0;
                var siblingNodeId, siblingNode, result, placement;
                
                // Search DOM for preceding or trailing priority list siblings
                for (i = 0; i < this.priorityList.length; i++) 
                {
                    if (i != idx) 
                    {
                        siblingNodeId = this.priorityList[i] + "-Legend";
                        result = dojo.byId(siblingNodeId);
                        if (result) 
                        {
                            siblingNode = result;
                        }
                    }
                    
                    if (siblingNode) 
                    {
                        if (i == idx) 
                        {
                            // A higher priority node has been found
                            placement = "after";
                            break;
                        }
                        else if (i > idx) 
                        {
                            // A lower priority node has been found
                            placement = "before";
                            break;
                        }
                    }
                }
                
                // Place the legend
                if (siblingNode) 
                {
                    dojo.place(legend.domNode, siblingNode, placement);
                }
                else 
                {
                    // If no siblings are found, place first
                    dojo.place(legend.domNode, this.tocContent, "first");
                }
                
                break;
        }
    },
    
    _onLayerRemoved: function(layer)
    {
        var legendId = layer.id + "-Legend";
        this._removeServiceLegend(legendId);
    },
    
    _removeServiceLegend: function(legendId)
    {
        var legendNode = dojo.byId(legendId);
        if (legendNode) 
        {
            var legendDijit = dijit.byNode(legendNode);
            
            if (legendDijit) 
            {
                // Destroy the legend dijit
                legendDijit.destroy();
            }
            
            // Destroy the legend HTML 
            dojo.destroy(legendId);
        }
    }
};

dojo.declare("dijits.tableOfContents.TableOfContents", [dijit._Widget, dijit._Templated], TableOfContents);
