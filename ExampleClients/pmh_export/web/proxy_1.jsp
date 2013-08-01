<%@page session="false"%>
<%@page import="java.net.*,java.io.*" %>
<%!
     // URL For Service or Service that are exportable from this client
     String exportableMapService = "http://localhost:8399/arcgis/rest/services/pmh";

     // URL to the export map service internal allows export from internal servers
     String mapServerTool = "http://localhost:8399/arcgis/rest/services/gptools/mapServerTools/GPServer/exportMapServerService";

     // Output folder where the export job results are placed (Only accessible via proxy)
     String serverOutputPath = "http://gwnw341:8399/arcgis/server/arcgisjobs";

     String[] serverUrls = {
        //"<url>[,<token>]"
        //For ex. (secured server): "http://myserver.mycompany.com/arcgis/rest/services,ayn2C2iPvqjeqWoXwV6rjmr43kyo23mhIPnXz2CEiMA6rVu0xR0St8gKsd0olv8a"
        //For ex. (non-secured server): "http://sampleserver1.arcgisonline.com/arcgis/rest/services"
        "https://egeoint.nrlssc.navy.mil/arcnga/services",
        "http://server.arcgisonline.com/ArcGIS/rest/services",
        "http://services.arcgisonline.com/ArcGIS/rest/services",
        exportableMapService,
        mapServerTool,
        serverOutputPath
    /*
    "http://egeoapp2:8399/arcgis/rest/services/pmh",
    "http://egeoapp1:8399/arcgis/rest/services/gptools/mapServerTools/GPServer/exportMapServerService",
    "http://egeoapp1:8399/arcgis/server/arcgisjobs"
     */
    };
%>
<% 
            
            try {
                String reqUrl = request.getQueryString();
                boolean allowed = false;
                String token = null;
                for (String surl : serverUrls) {
                    String[] stokens = surl.split("\\s*,\\s*");
                    if (reqUrl.toLowerCase().contains(stokens[0].toLowerCase())) {
                        allowed = true;
                        if (stokens[0].equalsIgnoreCase(serverOutputPath)) {
                            // Set the return filename to export.zip
                            response.setHeader("Content-Disposition", "inline; filename=export.zip;");
                        }

                        // Need to check gptools request to ensure submit includes the export service in the URL
                        // This could be spoofed (Need to break down the decoded URL and insure inMapServerURL parameter
                        
                        System.out.println("reqUrl: " + reqUrl);
                        if (reqUrl.toLowerCase().contains("submitjob")) {
                            String decodedReqUrl = URLDecoder.decode(reqUrl, "UTF-8");
                            System.out.println("decodedReqUrl: " + decodedReqUrl);
                            if (!decodedReqUrl.toLowerCase().contains(exportableMapService.toLowerCase())) {
                                // The queryString must include the exportable map URL
                                System.out.println("No no no!");
                                allowed = false;
                            }
                        }
                        if (stokens.length >= 2 && stokens[1].length() > 0) {
                            token = stokens[1];
                        }
                        break;
                    }
                }
                if (!allowed) {
                    response.setStatus(403);
                    return;
                }
                if (token != null) {
                    reqUrl = reqUrl + (reqUrl.indexOf("?") > -1 ? "&" : "?") + "token=" + token;
                }
                URL url = new URL(reqUrl);
                HttpURLConnection con = (HttpURLConnection) url.openConnection();
                con.setDoOutput(true);
                con.setRequestMethod(request.getMethod());
                if (request.getContentType() != null) {
                    con.setRequestProperty("Content-Type", request.getContentType());
                }
                int clength = request.getContentLength();
                if (clength > 0) {
                    con.setDoInput(true);
                    InputStream istream = request.getInputStream();
                    OutputStream os = con.getOutputStream();
                    final int length = 5000;
                    byte[] bytes = new byte[length];
                    int bytesRead = 0;
                    while ((bytesRead = istream.read(bytes, 0, length)) > 0) {
                        os.write(bytes, 0, bytesRead);
                    }
                }
                out.clear();
                out = pageContext.pushBody();
                OutputStream ostream = response.getOutputStream();
                response.setContentType(con.getContentType());
                InputStream in = con.getInputStream();
                final int length = 5000;
                byte[] bytes = new byte[length];
                int bytesRead = 0;
                while ((bytesRead = in.read(bytes, 0, length)) > 0) {
                    ostream.write(bytes, 0, bytesRead);
                }
            } catch (Exception e) {
                response.setStatus(500);
            }
%>
