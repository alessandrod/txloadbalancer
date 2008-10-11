# XXX this was put here for convenience, from the old code base
# needs to be moved into a static file
adminCSS = """
    body {
        font-family: helvetica;
        font-size: 10pt
    }
    a {
        text-decoration: none;
        background-color: transparent;
    }

    A:link {color: #000000 }
    A:visited {color: #000000}
    /* borrowed ideas from plone */
    div.footer {
        font-family: courier;
        font-size: 8pt ;
        background: transparent;
        border-collapse: collapse;
        border-top-color: #88AAAA;
        border-top-style: solid;
        border-top-width: 1px;
        padding: 0em 0em 0.5em 2em;
        white-space: nowrap;
        color: #000033 ;
    }

    div.footer a {
        background: transparent;
        border-color: #88AAAA;
        border-width: 1px;
        border-style: none solid solid solid;
        color: #226666;
        font-weight: normal;
        margin-right: 0.5em;
        padding: 0em 2em;
        text-transform: lowercase;
    }

    div.footer a:hover {
        background: #DEE7EC;
        border-color: #88AAAA;
        border-top-color: #88AAAA;
        color: #436976;
    }

    div.title {
        font-weight: bold;
        color: #000033 ;
        background: transparent;
        border-color: #88AAAA;
        border-style: none solid solid solid ;
        border-width: 1px;
        margin: 4px;
        padding: 3px;
        white-space: nowrap;
    }
    div.deleteButton {
        color: red ;
        background: yellow;
        border-collapse: collapse;
        border-color: red;
        border-style: solid solid solid solid ;
        border-width: 1px;
        padding: 1px;
        white-space: nowrap;
    }

    div.deleteButton a {
      color: black;
    }

    div.deleteButton a:hover {
      color: red;
    }

    p.message {
        color: #000000 ;
        background-color: #eeeeee ;
        border: thin solid #ff0000 ;
        padding: 5px ;
    }
    p.bigbutton {
        color: #000000 ;
        background-color: #eebbee ;
        border: thin solid #cc4400 ;
        padding: 2px ;
    }
    a.button {
        color: #000000 ;
        background-color: #eebbee ;
        border: thin solid #cc4400 ;
        padding: 4px ;
        margin: 2px ;
    }


    tr.enabled {
        background-color: #ccdddd;
        color: #dd0000
    }
    tr.inactive {
        background-color: #eeeeee;
        color: #000000
    }
    tr.inactive td.servHeader a {
        background-color: #ccdddd;
        color: #000000 ;
        padding: 0px 2px 0px 2px;
        border-style: solid;
        border-width: 1px;
    }
    tr.inactive td.servHeader a:hover {
        background-color: #ccdddd;
        color: red
    }

    th {
        font-family: helvetica ;
        font-size: 10pt ;
    }

    td {
        font: 10px helvetica;

    }

    td.addWidget {
        padding: 0px;
    }
    table.addWidget {
        padding: 0px;
    }

    /*table.addWidget td {
        font: 10px helvetica;
        background-color: white;
        margin: 0em 0em 0em 0em;
    }
    */

    div.widgetLabel {
        background-color: transparent;
        font-weight: bold;
        margin: 0em 0em 0em 0em;
    }

    input {
    /* Small cosmetic fix which makes input gadgets look nicer. */
        font: 10px Verdana, Helvetica, Arial, sans-serif;
        border: 1px solid #8cacbb;
        color: Black;
        background-color: white;
        margin: 0em 0em 0em 0em;
    }

    input:hover {
       background-color: #DEE7EC ;
    }

    p.copyright {
        font-weight: bold;
        max-width: 60%;
    }
    p.license {
        font-weight: bold;
        max-width: 60%;
    }
"""
