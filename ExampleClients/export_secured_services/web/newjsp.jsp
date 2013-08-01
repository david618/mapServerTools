<%-- 
    Document   : newjsp
    Created on : Jun 25, 2012, 1:47:07 PM
    Author     : jenningd
--%>

<%@page contentType="text/html" 
        pageEncoding="UTF-8"
        import="java.util.Enumeration"%>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
   "http://www.w3.org/TR/html4/loose.dtd">

<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        
        <title>JSP Page</title>
    </head>
    <body>
        <% Enumeration headerNames = request.getHeaderNames(); 
        while (headerNames.hasMoreElements()){
            String headerName = (String) headerNames.nextElement();
            String value = request.getHeader(headerName);
            out.println("<h2>" + headerName + " : " + value + "</h2>");
        }

        String serverName = request.getServerName();
        String contextPath = request.getContextPath();
        String requestURI = request.getRequestURI();
        String queryString = request.getQueryString();

        out.println("<h2>" + serverName + "</h2>");
        out.println("<h2>" + contextPath + "</h2>");
        out.println("<h2>" + requestURI + "</h2>");
        out.println("<h2>" + queryString + "</h2>");

        %>

        <h1>Hello World!</h1>
    </body>
</html>
