import genshi.template

# To make more output formats available to sqlpython, just edit this
# file, or place a copy in your local directory and edit that.

output_templates = {

'\\x': genshi.template.NewTextTemplate("""
<xml>
  <${tblname}_resultset>{% for row in rows %}
    <$tblname>{% for (colname, itm) in zip(colnames, row) %}
      <${colname.lower()}>$itm</${colname.lower()}>{% end %}
    </$tblname>{% end %}
  </${tblname}_resultset>
</xml>"""),

'\\j': genshi.template.NewTextTemplate("""
{"${tblname}": [
${',\\n'.join('        {%s}' % ', '.join('"%s": %s' % (colname,
        ((isinstance(itm,int) or isinstance(itm,float)) and '%s' or '"%s"') % str(itm)
    ) for (colname, itm) in zip(colnames, row)) for row in rows)}
    ]
}"""),  


'\\h': genshi.template.MarkupTemplate("""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns:py="http://genshi.edgewall.org/" xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
  <head>
    <title py:content="tblname">Table Name</title>
    <meta http-equiv="content-type" content="text/html;charset=utf-8" />
  </head>
  <body>
    <table py:attrs="{'id':tblname, 
     'summary':'Result set from query on table ' + tblname}">
      <tr>
        <th py:for="colname in colnames"
         py:attrs="{'id':'header_' + colname.lower()}">
          <span py:replace="colname.lower()">Column Name</span>
        </th>
      </tr>
      <tr py:for="row in rows">
        <td py:for="(colname, itm) in zip(colnames, row)" py:attrs="{'headers':'header_' + colname.lower()}">
          <span py:replace="str(itm)">Value</span>
        </td>
      </tr>
    </table>
  </body>
</html>"""),

'\\g': genshi.template.NewTextTemplate("""
{% for (rowNum, row) in enumerate(rows) %}
**** Row: ${rowNum + 1}
{% for (colname, itm) in zip(colnames, row) %}$colname: $itm
{% end %}{% end %}"""),

'\\G': genshi.template.NewTextTemplate("""
{% for (rowNum, row) in enumerate(rows) %}
**** Row: ${rowNum + 1}
{% for (colname, itm) in zip(colnames, row) %}${colname.ljust(colnamelen)}: $itm
{% end %}{% end %}"""),

'\\i': genshi.template.NewTextTemplate("""{% for (rowNum, row) in enumerate(rows) %}
INSERT INTO $tblname (${', '.join(colnames)}) VALUES (${', '.join(f % r for (r,f) in zip(row, formatters))});{% end %}"""),

'\\c': genshi.template.NewTextTemplate("""
${','.join(colnames)}{% for row in rows %}
${','.join('"%s"' % val for val in row)}{% end %}"""),

'\\C': genshi.template.NewTextTemplate("""
{% for row in rows %}${','.join('"%s"' % val for val in row)}{% end %}""")

}

output_templates['\\s'] = output_templates['\\c']
output_templates['\\S'] = output_templates['\\C']
