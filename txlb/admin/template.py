# takes a title and an optional strings substition, such as the value of a
# refresh template
head = """
    <html>
    <head>
    <title>%s</title>
    <link rel=stylesheet type="text/css" href="/txlb.css">
    %s
    </head>
    """


# takes two string substitutions: time in seconds and refresh URL
refresh = """
    <META HTTP-EQUIV=Refresh CONTENT="%s; URL=%s">
    """


# takes a message
message = '<p class="message">%s</p>'


# takes a title, optional refresh, project name, version, hostname and an
# optional message
header = head + """
    <body>
    <div class="title">%s version %s, running on host %s.</div>
    """


# takes the project URL and an optional message
footer = """
    <div class="footer">
    <a href="/">top</a>
    <a href="all">all</a>
    <a href="config.obj">running config</a>
    <a href="config.xml">disk config</a>
    <a href="%s">%s</a>
    </div>
    %s
    </body>
    </html>
    """


startRefresh = """
    <a class="button" href="/all?refresh=1&ignore=%s">Start
    auto-refresh</a></p>
    """


stopRefresh = """
    <a class="button" href="/all?ignore=%s">Stop auto-refresh</a></p>
    """


# takes an update time, a refresh time, and stop/start html
refreshButtons = """
    <p><b>current config</b></p>
    <p>last update at %s</p>
    <p><a class="button" href="/all?ignore=%s">Refresh</a>
    %s
    """


# takes a service name
serviceName = """
    <table><tr><th align="left" colspan="1">Service: %s</th></tr>
    """


# takes an ip:port string
listeningService = """
    <tr><td colspan="1">Listening on %s</td></tr>
    """


# takes a CSS class and a group name
groupName = """
    <tr class="%s"><td colspan="5" class="servHeader">%s
    """


# takes no substituion
groupDescEnabled = """
    <b>ENABLED</b>
    """


# takes the service name and the group name
groupDescDisabled = """
    <a href="enableGroup?service=%s&group=%s">enable</a>
    """


# takes the service name, group name, and CSS class
groupHeaderForm = """
    </td><td valign="top" rowspan="2" class="addWidget">
    <table class="addWidget">
    <form method="GET" action="addHost">
    <input type="hidden" name="service" value="%s">
    <input type="hidden" name="group" value="%s">
    <tr>
        <td><div class="widgetLabel">name</div>
        </td>
        <td><input name="name" type="text" size="15">
        </td>
    </tr>
    <tr>
        <td><div class="widgetLabel">ip</div>
        </td>
        <td><input name="ip" type="text" size="15">
        </td>
    </tr>
    <tr>
        <td colspan=2 align="center"><input type="submit" value="add host">
        </td>
    </tr>
    </form>
    </table>
    </td>
    </tr>
    <tr class="%s">
    <th colspan="2">hosts</th><th>open</th><th>total</th><th>failed</th>
    </tr>
    """


# takes CSS class, hostname, host, open connections, total connections as well
# as urllib-quoted service name, group name, and host
hostInfo = """
    <tr class="%s">
    <td>%s</td><td><tt>%s</tt></td>
    <td>%s</td><td>%s</td><td>%s</td>
    <td><div class="deleteButton">
    <a href="delHost?service=%s&group=%s&ip=%s">remove host</a>
    </div></td>
    </tr>
    """


# takes a CSS class
badHostGroup = """
    <tr class="%s"><th colspan="2">disabled hosts</th>
    <th>why</th><th>when</th></tr>
    """


# takes a CSS class, hostname, host, and error message
badHostInfo = """
    <tr class="%s"><td>
    %s</td><td><tt>%s</tt></td>
    <td>%s</td><td>--</td>
    </tr>
    """


serviceClose = """
    </table>
    """


unauth = """
    <html><body>Access Denied.</body></html>
    """
