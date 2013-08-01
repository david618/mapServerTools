dojo.provide('dijits.Utilities');

dijits.Utilities = {
    /* Dom Functions */
    addCss: function(cssArray)
    {
        // load CSS files passed in the cssArray
        var head = document.getElementsByTagName("head").item(0);
        
        if (head) 
        {
            for (var i = 0, il = cssArray.length; i < il; i++) 
            {
                var link = document.createElement("link");
                link.type = "text/css";
                link.rel = "stylesheet";
                link.href = cssArray[i].toString();
                head.appendChild(link);
            }
        }
    },
    showControl: function(control, isShow)
    {
        if (!control) 
        {
            return;
        }
        
        var cont;
        if (control.domNode) 
        {
            cont = control.domNode;
        }
        else 
        {
            cont = control;
        }
        
        if (isShow) 
        {
            dojo.removeClass(cont, 'hide');
        }
        else 
        {
            dojo.addClass(cont, 'hide');
        }
    },
    animateDialogOut: function(node, func)
    {
        var slideArgs = {
            node: node,
            top: (dojo.coords(node).t).toString(),
            left: (dojo.coords(node).l + 300).toString(),
            unit: 'px',
            duration: 350,
            onEnd: function(node)
            {
                if (dijit.byId(node.id) !== undefined) 
                {
                    dijit.byId(node.id).destroyRecursive(false);
                }
                if (func !== null) 
                {
                    func();
                }
            }
        };
        var fadeArgs = {
            node: node,
            duration: 300,
            onEnd: function(node)
            {
                if (dijit.byId(node.id) !== undefined) 
                {
                    dijit.byId(node.id).hide();
                }
            }
        };
        dojo.fx.combine([dojo.fx.slideTo(slideArgs), dojo.fadeOut(fadeArgs)]).play();
    },
    destroyNode: function(node)
    {
        // See if node is a node or just the name of a node.
        if (!node.id) 
        {
            node = dojo.byId(node);
        }
        
        if (node) 
        {
            // If the node already exists, destroy it.
            if (dijit.byId(node.id) !== undefined) 
            {
                dijit.byId(node.id).destroyRecursive(false);
                // Node destroyed, return true;
                return true;
            }
        }
        
        // Nothing to destroy, return false;
        return false;
    },
    fadeIn: function(node, durationSeconds)
    {
        stlrat.Utilities.showControl(node, true);
        
        var duration = durationSeconds * 100;
        var fadeArgs = {
            node: node,
            duration: duration,
            onEnd: function(node)
            {
            
            }
        };
        dojo.fadeIn(fadeArgs).play();
    },
    fadeOut: function(node, durationSeconds, secondsBeforeFade)
    {
        var duration = durationSeconds * 1000;
        var interval = secondsBeforeFade * 1000 || 1000;
        
        var timer = new dojox.timing.Timer();
        timer.setInterval(interval);
        
        dojo.connect(timer, 'onTick', function()
        {
            var fadeArgs = {
                node: node,
                duration: duration,
                onEnd: function(node)
                {
                    // console.log(dijit.byId(node.id) !== undefined);
                    if (dijit.byId(node.id) !== undefined) 
                    {
                        dijit.byId(node.id).hide();
                    }
                    else 
                    {
                        //     console.log(node);
                        stlrat.Utilities.showControl(node, false);
                    }
                }
            };
            
            dojo.fadeOut(fadeArgs).play();
            
            timer.stop();
            timer = null;
        });
        
        timer.start();
    },
    fadeInOut: function(node, inSeconds, outSeconds, secondsBeforeFadeOut)
    {
        stlrat.Utilities.showControl(node, true);
        dojo.style(node, 'opacity', '50');
        
        var inDuration = inSeconds * 1000;
        var fadeInArgs = {
            node: node,
            duration: inDuration,
            onEnd: function(node)
            {
                var outDuration = outSeconds * 1000;
                var interval = secondsBeforeFadeOut * 1000 || 1000;
                var timer = new dojox.timing.Timer();
                timer.setInterval(interval);
                
                dojo.connect(timer, 'onTick', function()
                {
                    dojo.style(node, 'opacity', '1');
                    var fadeArgs = {
                        node: node,
                        duration: outDuration,
                        onEnd: function(node)
                        {
                            stlrat.Utilities.showControl(node, false);
                        }
                    };
                    
                    dojo.fadeOut(fadeArgs).play();
                    
                    timer.stop();
                    timer = null;
                });
                
                timer.start();
            }
        };
        
        dojo.fadeIn(fadeInArgs).play();
    },
    
    /* Map Related Methods */
    createSimpleMapLayer: function(type, id, url)
    {
        // Layer            
        var options = {
            id: id,
            visible: true
        };
        
        switch (type)
        {
            case 'cached':
            case 'tiled':
                return new esri.layers.ArcGISTiledMapServiceLayer(url, options);
                break;
            case 'dynamic':
                return esri.layers.ArcGISDynamicMapServiceLayer(url, options);
                break;
            case 'wms':
                return esri.layers.WMSLayer(url, options);
        }
    },
    setLayerOpacity: function(layer, opacity)
    {
        if (opacity > 1) 
        {
            opacity = opacity / 100;
        }
        
        layer.setOpacity(opacity);
    },
    projectGeometryToMap: function(geometry, map)
    {
        // Same - return geometry
        if ((this.isWGS84(geometry) && this.isWGS84(map)) ||
        this.isWebMercator(geometry) && this.isWebMercator(map)) 
        {
            // console.info('Same wkid - No conversion needed.');
            return geometry;
        }
        // Map WebMercator - Geometry is not
        if (this.isWebMercator(map) && this.isWGS84(geometry)) 
        {
            // console.info('Map WebMercator - Geometry is not - Converting...');
            return esri.geometry.geographicToWebMercator(geometry);
        }
        // Map WGS84 - Geometry is not
        if (this.isWGS84(map) && this.isWebMercator(geometry)) 
        {
            // console.info('Map WGS84 - Geometry is not - Converting...');
            return esri.geometry.webMercatorToGeographic(geometry);
        }
        console.warn('unable to reproject geometry');
        return geometry;
    },
    isWebMercator: function(wkid)
    {
        if (wkid.spatialReference && wkid.spatialReference.wkid) 
        {
            wkid = wkid.spatialReference.wkid;
        }
        // == not === since the wkid might be a string or an int
        return (wkid == 102100 || wkid == 102113 || wkid == 3857);
    },
    isWGS84: function(wkid)
    {
        if (wkid.spatialReference && wkid.spatialReference.wkid) 
        {
            wkid = wkid.spatialReference.wkid;
        }
        // == not === since the wkid might be a string or an int
        return (wkid == 4326);
    },
    getFeatureLayerMode: function(mode)
    {
        dojo.require("esri.layers.FeatureLayer");
        
        switch (mode)
        {
            case 'onDemand':
            case 'MODE_ONDEMAND':
                return esri.layers.FeatureLayer.MODE_ONDEMAND;
            case 'selection':
            case 'MODE_SELECTION':
                return esri.layers.FeatureLayer.MODE_SELECTION;
            case 'snapshot':
            case 'MODE_SNAPSHOT':
                return esri.layers.FeatureLayer.MODE_SNAPSHOT;
        }
    },
    // TODO: geometryToDMS
    
    wgs84ToDMS: function(coord)
    {
        var dms = dojo.number.round(coord, 3);
        
        return dms;
    },
    dmsToWGS84: function(coord)
    {
        var wgs84 = dojo.number.round(coord, 3);
        
        return wgs84;
    },
    
    simpleColorByNumber: function(index)
    {
        if (index % 9 === 1) 
        {
            return dojo.colorFromHex('#FF0000');
        }
        else if (index % 9 === 2) 
        {
            return dojo.colorFromHex('#FF6600');
        }
        else if (index % 9 === 3) 
        {
            return dojo.colorFromHex('#FFFF00');
        }
        else if (index % 9 === 4) 
        {
            return dojo.colorFromHex('#009900');
        }
        else if (index % 9 === 5) 
        {
            return dojo.colorFromHex('#0066FF');
        }
        else if (index % 9 === 6) 
        {
            return dojo.colorFromHex('#6600FF');
        }
        else if (index % 9 === 7) 
        {
            return dojo.colorFromHex('#996600');
        }
        else if (index % 9 === 8) 
        {
            return dojo.colorFromHex('#CC99CC');
        }
        else if (index % 9 === 0) 
        {
            return dojo.colorFromHex('#33CC99');
        }
    },
    
    /* Array helpers */
    getPositionInArray: function(index, length)
    {
        if (index === 0) 
        {
            return 'first';
        }
        else if (index > 0 && index < length - 1) 
        {
            return 'middle';
        }
        else if (index === length - 1) 
        {
            return 'last';
        }
        else 
        {
            return 'outside';
        }
    },
    removeItemInArray: function(array, item)
    {
        var index = array.indexOf(item); // Find the index
        if (index != -1) 
            array.splice(index, 1); // Remove it if really found!
        // console.log(array);
    },
    
    /* String helpers */
    getLetterByIndex: function(index)
    {
        return String.fromCharCode(65 + index);
    },
    replaceString: function(obj, search, replace)
    {
        return obj.split(search).join(replace);
    },
    startsWithVowel: function(text)
    {
        var firstLetter = text.substring(0, 1);
        switch (firstLetter.toLowerCase())
        {
            case 'a':
            case 'e':
            case 'i':
            case 'o':
            case 'u':
                return true;
            default:
                return false;
        }
    },
    
    // Takes a hyphenated string and returns a camelCased version of it
    // example: border-top-color --> borderTopColor
    hyphenatedToCamelCase: function(hyphenatedStr)
    {
        var allCaps = hyphenatedStr.toUpperCase();
        var camelCaseArray = hyphenatedStr.split("");
        var hyphenCnt = 0;
        for (var i = 0; i < hyphenatedStr.length; i++) 
        {
            if (hyphenatedStr[i] === "-") 
            {
                camelCaseArray[i - hyphenCnt] = allCaps[i + 1];
                hyphenCnt++;
                i++;
            }
            else 
            {
                camelCaseArray[i - hyphenCnt] = hyphenatedStr[i];
            }
            
        }
        
        return camelCaseArray.join("").substr(0, hyphenatedStr.length - hyphenCnt);
    },
    
    // Functions for turning a CSS style string into an associative array
    parseStyle: function(styleStr, keepShorthand)
    {
        dojo.require('dijits.ExtendFunctionality');

        // Split into individual styles
        var styleStrings = styleStr.split(";");
        
        // create associative array of styles
        var styles = [];
        var stylePair;
        dojo.forEach(styleStrings, function(styleString)
        {
            if (styleString !== "") 
            {
                stylePair = styleString.split(":");
                stylePair[0] = stylePair[0].trim();
                stylePair[1] = stylePair[1].trim();
                styles[stylePair[0]] = stylePair[1];
            }
        });
        
        if (!keepShorthand) 
        {
            // Break out padding style
            if (styles.padding) 
            {
                this._breakoutShorthandStyle("padding", styles);
            }
            
            // Break out margin style
            if (styles.margin) 
            {
                this._breakoutShorthandStyle("margin", styles);
            }
            
            // Break out border-width style
            if (styles["border-width"]) 
            {
                this._breakoutShorthandStyle("border-width", styles);
            }
            
            // Break out border-style style
            if (styles["border-style"]) 
            {
                this._breakoutShorthandStyle("border-style", styles);
            }
            
            // Break out border-color style
            if (styles["border-color"]) 
            {
                this._breakoutShorthandStyle("border-color", styles);
            }
            
            // Break out border-color style
            if (styles.border) 
            {
                this._breakoutShorthandStyle("border", styles);
            }
        }
        
        return styles;
    },
    
    _breakoutShorthandStyle: function(property, styleArray)
    {
        var valueStr = styleArray[property];
        var values = valueStr.split(" ");
        
        var topProp, leftProp, bottomProp, rightProp;
        var splitPropName = property.split("-");
        if (splitPropName.length > 1) 
        {
            topProp = splitPropName[0] + "-top-" + splitPropName[1];
            leftProp = splitPropName[0] + "-left-" + splitPropName[1];
            bottomProp = splitPropName[0] + "-bottom-" + splitPropName[1];
            rightProp = splitPropName[0] + "-right-" + splitPropName[1];
        }
        else 
        {
            topProp = property + "-top";
            leftProp = property + "-left";
            bottomProp = property + "-bottom";
            rightProp = property + "-right";
        }
        
        if (property == "border") 
        {
            // Special case for border (border: width style color;)
            styleArray["border-top-width"] = values[0];
            styleArray["border-right-width"] = values[0];
            styleArray["border-bottom-width"] = values[0];
            styleArray["border-left-width"] = values[0];
            
            styleArray["border-top-style"] = values[1];
            styleArray["border-right-style"] = values[1];
            styleArray["border-bottom-style"] = values[1];
            styleArray["border-left-style"] = values[1];
            
            styleArray["border-top-color"] = values[2];
            styleArray["border-right-color"] = values[2];
            styleArray["border-bottom-color"] = values[2];
            styleArray["border-left-color"] = values[2];
        }
        else 
        {
            switch (values.length)
            {
                case (4):
                    styleArray[topProp] = values[0];
                    styleArray[rightProp] = values[1];
                    styleArray[bottomProp] = values[2];
                    styleArray[leftProp] = values[3];
                    break;
                case (3):
                    styleArray[topProp] = values[0];
                    styleArray[rightProp] = values[1];
                    styleArray[bottomProp] = values[2];
                    styleArray[leftProp] = values[1];
                    break;
                case (2):
                    styleArray[topProp] = values[0];
                    styleArray[rightProp] = values[1];
                    styleArray[bottomProp] = values[0];
                    styleArray[leftProp] = values[1];
                    break;
                case (1):
                    styleArray[topProp] = values[0];
                    styleArray[rightProp] = values[0];
                    styleArray[bottomProp] = values[0];
                    styleArray[leftProp] = values[0];
                    break;
            }
        }
        
        delete styleArray[property];
    },
    
    // Turns an associative array of CSS styles into a CSS string 
    styleArrayToString: function(styleArray)
    {
        var styleStr = "";
        
        for (var style in styleArray) 
        {
            styleStr += style + ":" + styleArray[style] + ";";
        }
        
        return styleStr;
    }
    
};


