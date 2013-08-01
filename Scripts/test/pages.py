
def makeLayerList(layerids):

    layerList = []
    try:
    
        layerids = layerids.strip()

        if layerids == "":
            raise Exception("Empty layerids string")

        layeridsParts = layerids.split(",")

        for layeridPart in layeridsParts:
            if layeridPart == "":
                # Empty layeridPart; extra commas
                continue
                
        
            layeridPartDash = layeridPart.split("-")
            partcnt = len(layeridPartDash)
            if partcnt == 1:
                # No dash assume it's a single number
                try:
                    layerid = int(layeridPart)
                except ValueError:
                    # Must be numbers
                    raise Exception("Invalid layer id: " + layeridPart)
                if not layerid in layerList:
                    layerList.append(layerid)
            elif partcnt == 2:
                # This is a range
                try:
                    lownum = int(layeridPartDash[0])
                except ValueError:
                    # Must be numbers
                    raise Exception("Invalid start number: " + layeridPart)
                try:
                    highnum = int(layeridPartDash[1])
                except ValueError:
                    # Must be numbers
                    raise Exception("Invalid end number: " + layeridPart)

                if highnum < lownum:
                    raise Exception("Invalid range: " + layeridPart)
                
                for i in range(lownum, highnum + 1):
                    if not i in layerList:
                        layerList.append(i)
                
            else:
                # invalid input
                print "Invalid part: " + layeridPart
                
        if len(layerList) == 0:
            raise Exception("Empty layerid list")

        return layerList
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    layerids = "1,2,3,5-20"
    layerList = makeLayerList(layerids)
    if type(layerList) is str:
        print layerList
    else:
        layerList.sort()
        print layerList
    
    
