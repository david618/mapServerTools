dojo.provide("dijits.controls.TabDrawer");

dojo.require("dijit._Widget");
dojo.require("dijit._Templated");
dojo.require("dijit.layout.TabContainer");
dojo.require("dijit.layout.ContentPane");
dojo.require("dijits.Utilities");
dojo.require("dojo.cache");

var TabDrawer = {
    templateString: dojo.cache("dijits.controls.TabDrawer", "templates/tabDrawerTemplate.html"),
    
    _menuPinned: false,
    _drawerOpen: false,
    _tabContainer: null,
    _parentNode: null,
    _fullHeight: null,
    _fullWidth: null,
    _origBottom: null,
    _origRight: null,
    
    // Attributes:
    style: "",
    placemnet: "right", // right, left, top, bottom
    postMixInProperties: function()
    {
        var styleArray = dijits.Utilities.parseStyle(this.style);
        
        // this thing requires a width and height.  If they didn't include one, shove in defaults
        if (!styleArray["width"]) 
        {
            styleArray["width"] = "350px";
        }
        if (!styleArray["height"]) 
        {
            styleArray["height"] = "350px";
        }
        if (!styleArray["z-index"]) 
        {
            styleArray["z-index"] = "100";
        }
        
        this._fullHeight = styleArray["height"];
        this._fullWidth = styleArray["width"];
        if (styleArray["bottom"] && this.placement != "bottom") 
        {
            this._origBottom = styleArray["bottom"];
        }
        if (styleArray["right"] && this.placement != "right") 
        {
            this._origRight = styleArray["right"];
        }
        
        // update style based on this.placement
        /*
         * - right:  position:absolute; right:-width; padding-right:0px; margin-right:0px;
         * - left:   position:absolute; left:-width; padding-left:0px; margin-left:0px;
         * - top:    position:absolute; top:-height; padding-top:0px; margin-top:0px;
         * - bottom: position:absolute; bottom:-height; padding-bottom:0px; margin-bottom:0px;
         */
        switch (this.placement)
        {
            case ("left"):
                styleArray["position"] = "absolute";
                styleArray["left"] = "-" + styleArray["width"];
                styleArray["padding-left"] = "0px";
                styleArray["margin-left"] = "0px";
                delete styleArray["right"];
                break;
            case ("top"):
                styleArray["position"] = "absolute";
                styleArray["top"] = "-" + styleArray["height"];
                styleArray["padding-top"] = "0px";
                styleArray["margin-top"] = "0px";
                delete styleArray["bottom"];
                break;
            case ("bottom"):
                styleArray["position"] = "absolute";
                styleArray["bottom"] = "-" + styleArray["height"];
                styleArray["padding-bottom"] = "0px";
                styleArray["margin-bottom"] = "0px";
                delete styleArray["top"];
                break;
            default:
                // defaulting to the drawer on the right
                styleArray["position"] = "absolute";
                styleArray["right"] = "-" + styleArray["width"];
                styleArray["padding-right"] = "0px";
                styleArray["margin-right"] = "0px";
                delete styleArray["left"];
                break;
        }
        
        this.style = dijits.Utilities.styleArrayToString(styleArray);
    },
    
    postCreate: function()
    {
        var tabPosition;
        switch (this.placement)
        {
            case ("left"):
                tabPosition = "right-h";
                break;
            case ("top"):
                tabPosition = "bottom";
                break;
            case ("bottom"):
                tabPosition = "top";
                break;
            default:
                // defaulting to the drawer on the right
                tabPosition = "left-h";
                break;
        }
        
        // Creating tabContainer
        this._tabContainer = new dijit.layout.TabContainer({
            style: "height:100%;",
            doLayout: true,
            tabPosition: tabPosition
        }).placeAt(this.drawerContainer);
        
        this._initHandlers();
    },
    
    startup: function()
    {
        this._tabContainer.startup();
    },
    
    addTab: function(title)
    {
        var tabContentNode = dojo.create("div", {
            "class": "drawerMenuItemContainer"
        });
        
        var tabContentPane = new dijit.layout.ContentPane({
            title: title,
            content: tabContentNode
        });
        this._tabContainer.addChild(tabContentPane);
        
        this._slideDrawer(this._drawerOpen);
        
        return tabContentNode;
    },
    
    _initHandlers: function()
    {
        dojo.connect(this._tabContainer.tablist.containerNode, "onclick", dojo.hitch(this, function(evt)
        {
            this._toggleDrawer(true);
        }));
        
        dojo.connect(this._tabContainer.domNode, "onmouseleave", dojo.hitch(this, function(evt)
        {
            //            var ctrlPos = dojo.position(this.drawerContainer);
            //            if ((evt.clientX < ctrlPos.x || evt.clientX > (ctrlPos.x + ctrlPos.w)) || (evt.clientY < ctrlPos.y || evt.clientY > (ctrlPos.y + ctrlPos.h))) 
            //            {
            //            
            //                this._toggleDrawer(false);
            //            }
            this._toggleDrawer(false);
        }));
    },
    
    _toggleDrawer: function(open)
    {
        if (open && !this._drawerOpen) 
        {
            this._slideDrawer(true);
        }
        if (!open && this._drawerOpen) 
        {
            this._slideDrawer(false);
        }
    },
    
    _slideDrawer: function(open)
    {
        this._drawerOpen = open;
        
        // Restore the tab drawer control to its original size
        this._restoreTabDrawer(open);
        
        var animProps;
        var node = dojo.marginBox(this.drawerContainer);
        var tabs = dojo.marginBox(this._tabContainer.tablist.domNode);
        
        var dis;
        switch (this.placement)
        {
            case ("left"):
                dis = (open) ? 0 : (node.w - tabs.w) * -1;
                animProps = {
                    left: dis
                };
                break;
            case ("top"):
                dis = (open) ? 0 : (node.h - tabs.h) * -1;
                animProps = {
                    top: dis
                };
                break;
            case ("bottom"):
                dis = (open) ? 0 : (node.h - tabs.h) * -1;
                animProps = {
                    bottom: dis
                };
                break;
            default:
                dis = (open) ? 0 : (node.w - tabs.w) * -1;
                animProps = {
                    right: dis
                };
                break;
        }
        
        dojo.animateProperty({
            node: this.drawerContainer,
            properties: animProps,
            onEnd: dojo.hitch(this, function(node)
            {
                // Collapse the tab drawer control to the size of the tabs only 
                this._collapseTabDrawer(open);
            })
        }).play();
    },
    
    _restoreTabDrawer: function(open)
    {
        if (open) 
        {
            var collapsedMarginBox = dojo.marginBox(this.drawerContainer);
			
			// set control to full size
            dojo.style(this.drawerContainer, "height", this._fullHeight);
            dojo.style(this.drawerContainer, "width", this._fullWidth);
            
            switch (this.placement)
            {
                case "right":
                case "left":
                    if (this._origBottom) 
                    {
                        dojo.style(this.drawerContainer, "bottom", this._origBottom);
                    }
                    
                    var dw = parseInt(this._fullWidth) - collapsedMarginBox.w;
					if(this.placement == "left")
					{
						dojo.style(this.drawerContainer, "left", -dw + "px");
					}
					else
					{
                        dojo.style(this.drawerContainer, "right", -dw + "px");
					}
                    break;
                case "top":
                case "bottom":
                    if (this._origRight) 
                    {
                        dojo.style(this.drawerContainer, "right", this._origRight);
                    }

                    var dh = parseInt(this._fullHeight) - collapsedMarginBox.h;
                    if(this.placement == "bottom")
                    {
                        dojo.style(this.drawerContainer, "bottom", -dh + "px");
                    }
                    else
                    {
                        dojo.style(this.drawerContainer, "top", -dh + "px");
                    }
                    break;
            }
            
            this._tabContainer.resize();
        }
    },
    
    _collapseTabDrawer: function(open)
    {
        var tabNodes = dojo.query(">", this._tabContainer.tablist.containerNode);
        var tablistMarginBox = dojo.marginBox(this._tabContainer.tablist.containerNode);
        var marginBox;
        var tabNodesHeightSum = 0;
        var tabNodesWidthSum = 0;
        dojo.forEach(tabNodes, function(tabNode)
        {
            marginBox = dojo.marginBox(tabNode);
            tabNodesHeightSum += marginBox.h;
            tabNodesWidthSum += marginBox.w;
        });
		// Add in padding pixels equal to the number of tabs - 1 to make sure we don't end 
		// up with tab scroll buttons once control is collapsed
		tabNodesWidthSum += tabNodes.length - 1;
        
        if (!open) 
        {
            // collapse control to tab dimensions only
            switch (this.placement)
            {
                case "right":
                case "left":
                    // correct for a bottom value set
                    if (this._origBottom) 
                    {
                        var bottom = parseInt(this._origBottom);
                        var fullHeight = parseInt(this._fullHeight);
                        var newBottom = bottom + (fullHeight - tabNodesHeightSum)
                        dojo.style(this.drawerContainer, "bottom", newBottom + "px");
                    }
                    
                    // Resize the control
					dojo.style(this.drawerContainer, "height", tabNodesHeightSum + "px");
                    dojo.style(this.drawerContainer, "width", tablistMarginBox.w + "px");

                    // Position the control against the wall
					if (this.placement == "right") 
                    {
                        dojo.style(this.drawerContainer, "right", "0px");
                    }
                    else 
                    {
                        dojo.style(this.drawerContainer, "left", "0px");
                    }

                    break;
                case "top":
                case "bottom":

                    // Shrink to proper width
                    dojo.style(this.drawerContainer, "width", this._fullWidth);
                    var fullWidth = dojo.style(this.drawerContainer, "width");
                    if (tabNodesWidthSum < fullWidth) 
                    {
                        dojo.style(this.drawerContainer, "width", tabNodesWidthSum + "px");
                    }

                    //correct for a right value set
                    if (this._origRight) 
                    {
                        var newRight = parseInt(this._origRight) + (parseInt(this._fullWidth) - tabNodesWidthSum);
                        dojo.style(this.drawerContainer, "right", newRight + "px");
                    }

                    // Shrink to height of tabs
					dojo.style(this.drawerContainer, "height", tablistMarginBox.h + "px");

                    // Position the control against the floor/ceiling
                    if (this.placement == "bottom") 
                    {
                        dojo.style(this.drawerContainer, "bottom", "0px");
                    }
                    else 
                    {
                        dojo.style(this.drawerContainer, "top", "0px");
                    }

                    break;
            }
            this._tabContainer.resize();
        }
    }
};

dojo.declare("dijits.controls.TabDrawer", [dijit._Widget, dijit._Templated], TabDrawer);
