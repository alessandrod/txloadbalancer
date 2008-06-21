# takes an optional strings substition, such as the value of a refresh template
head = """
    <html>
    <head>
    <title>python director</title>
    <link rel=stylesheet type="text/css" href="/pydirector.css">
    %s
    </head>
    """

# takes two string substitutions: time in seconds and refresh URL
refresh = """
    <META HTTP-EQUIV=Refresh CONTENT="%s; URL=%s">
    """

# takes optional refresh, version, and hostname
header = head + """
    <body>
    <div class="title">Python Director version %s, running on host %s.</div>
    """

# takes a message
message = '<p class="message">%s</p>'

# takes the project URL and an optional message
footer = """
    <div class="footer">
    <a href="/">top</a>
    <a href="running">running</a>
    <a href="running.xml">running.xml</a>
    <a href="config.xml">config.xml</a>
    <a href="%s">pythondirector</a>
    </div>
    %s
    </body>
    </html>
    """
