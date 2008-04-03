"""sqlpyPlus - extra features (inspired by Oracle SQL*Plus) for Luca Canali's sqlpython.py

Features include:
 - SQL*Plus-style bind variables
 - Query result stored in special bind variable ":_" if one row, one item
 - SQL buffer with list, run, ed, get, etc.; unlike SQL*Plus, buffer stores session's full history
 - @script.sql loads and runs (like SQL*Plus)
 - ! runs operating-system command
 - show and set to control sqlpython parameters
 - SQL*Plus-style describe, spool
 - write sends query result directly to file
 - comments shows table and column comments
 - compare ... to ... graphically compares results of two queries
 - commands are case-insensitive
 
Use 'help' within sqlpython for details.

Compatible with sqlpython v1.3

Set bind variables the hard (SQL*Plus) way
exec :b = 3
or with a python-like shorthand
:b = 3

- catherinedevlin.blogspot.com  May 31, 2006
"""
# note in cmd.cmd about supporting emacs commands?

descQueries = {
'TABLE': ("""
 atc.column_name,
            CASE atc.nullable WHEN 'Y' THEN 'NULL' ELSE 'NOT NULL' END "Null?",
            atc.data_type ||
              CASE atc.data_type WHEN 'DATE' THEN ''
                             ELSE '(' ||
                               CASE atc.data_type WHEN 'NUMBER' THEN TO_CHAR(atc.data_precision) ||
                                 CASE atc.data_scale WHEN 0 THEN ''
                                                 ELSE ',' || TO_CHAR(atc.data_scale) END
                                              ELSE TO_CHAR(atc.data_length) END 
                             END ||
              CASE atc.data_type WHEN 'DATE' THEN '' ELSE ')' END
              data_type
FROM all_tab_columns atc
WHERE atc.table_name = :object_name
AND      atc.owner = :owner
ORDER BY atc.column_id;""",),
'PROCEDURE': ("""
             argument_name,             
             data_type,
             in_out,
             default_value
FROM all_arguments
WHERE object_name = :object_name
AND      owner = :owner
AND      package_name IS NULL
AND      argument_name IS NOT NULL
ORDER BY sequence;""",),    
'PackageObjects':("""
SELECT DISTINCT object_name
FROM all_arguments
WHERE package_name = :package_name
AND      owner = :owner""",),
'PackageObjArgs':("""
             object_name,
             argument_name,             
             data_type,
             in_out,
             default_value
FROM all_arguments
WHERE package_name = :package_name
AND      object_name = :object_name
AND      owner = :owner
AND      argument_name IS NOT NULL
ORDER BY sequence""",),
'TRIGGER':("""
       description
FROM   all_triggers
WHERE  owner = :owner
AND    trigger_name = :object_name
""",
"""
       table_owner,
       base_object_type,
       table_name,
       column_name,
       when_clause,
       status,
       action_type,
       crossedition
FROM   all_triggers
WHERE  owner = :owner
AND    trigger_name = :object_name
\\t
""",
),
'INDEX':("""
index_type,
table_owner,
table_name,
table_type,
uniqueness,
compression,
partitioned,
temporary,
generated,
secondary,
dropped,
visibility
FROM   all_indexes
WHERE  owner = :owner
AND    index_name = :object_name
\\t
""",)
    }
descQueries['VIEW'] = descQueries['TABLE']
descQueries['FUNCTION'] = descQueries['PROCEDURE']

queries = {
'resolve': """
SELECT object_type, object_name, owner FROM (
        SELECT object_type, object_name, user owner, 1 priority
        FROM   user_objects
        WHERE object_name = :objName
    UNION ALL
        SELECT ao.object_type, ao.object_name, ao.owner, 2 priority
        FROM    all_objects ao
        JOIN      user_synonyms us ON (us.table_owner = ao.owner AND us.table_name = ao.object_name)
        WHERE us.synonym_name = :objName
    AND   ao.object_type != 'SYNONYM'
    UNION ALL
        SELECT ao.object_type, ao.object_name, ao.owner, 3 priority
        FROM    all_objects ao
        JOIN      all_synonyms asyn ON (asyn.table_owner = ao.owner AND asyn.table_name = ao.object_name)
        WHERE asyn.synonym_name = :objName
    AND   ao.object_type != 'SYNONYM'
        AND      asyn.owner = 'PUBLIC'
    UNION ALL 
        SELECT 'DIRECTORY' object_type, dir.directory_name, dir.owner, 6 priority
        FROM   all_directories dir
        WHERE  dir.directory_name = :objName
    UNION ALL 
        SELECT 'DATABASE LINK' object_type, db_link, owner, 7 priority
        FROM   all_db_links dbl
        WHERE  dbl.db_link = :objName
) ORDER BY priority ASC""",
'tabComments': """
SELECT comments
FROM    all_tab_comments
WHERE owner = :owner
AND      table_name = :table_name""",
'colComments': """
atc.column_name,
             acc.comments             
FROM all_tab_columns atc
JOIN all_col_comments acc ON (atc.owner = acc.owner and atc.table_name = acc.table_name and atc.column_name = acc.column_name)
WHERE atc.table_name = :object_name
AND      atc.owner = :owner
ORDER BY atc.column_id;""",
#thanks to Senora.pm for "refs"
'refs': """
       NULL               referenced_by, 
       c2.table_name      references, 
       c1.constraint_name constraint
FROM
       user_constraints c1,
       user_constraints c2
WHERE
       c1.table_name = :object_name
       and c1.constraint_type ='R'
       and c1.r_constraint_name = c2.constraint_name
       and c1.r_owner = c2.owner
       and c1.owner = :owner
UNION
SELECT c1.table_name      referenced_by, 
       NULL               references, 
       c1.constraint_name constraint
FROM
       user_constraints c1,
       user_constraints c2
WHERE
       c2.table_name = :object_name
       and c1.constraint_type ='R'
       and c1.r_constraint_name = c2.constraint_name
       and c1.r_owner = c2.owner
       and c1.owner = :owner       
"""
}

import sys, os, re, sqlpython, cx_Oracle, pyparsing
from cmd2 import flagReader

if float(sys.version[:3]) < 2.3:
    def enumerate(lst):
        return zip(range(len(lst)), lst)
        
class SoftwareSearcher(object):
    def __init__(self, softwareList, purpose):
        self.softwareList = softwareList
        self.purpose = purpose
        self.software = None
    def invoke(self, *args):
        if not self.software:
            (self.software, self.invokeString) = self.find()            
        argTuple = tuple([self.software] + list(args))
        os.system(self.invokeString % argTuple)
    def find(self):
        if self.purpose == 'text editor':
            software = os.environ.get('EDITOR')
            if software:
                return (software, '%s %s')
        for (n, (software, invokeString)) in enumerate(self.softwareList):
            if os.path.exists(software):
                if n > (len(self.softwareList) * 0.7):
                    print """
    
    Using %s.  Note that there are better options available for %s,
    but %s couldn't find a better one in your PATH.
    Feel free to open up %s
    and customize it to find your favorite %s program.
    
    """ % (software, self.purpose, __file__, __file__, self.purpose)
                return (software, invokeString)
            stem = os.path.split(software)[1]
            for p in os.environ['PATH'].split(os.pathsep):
                if os.path.exists(os.sep.join([p, stem])):
                    return (stem, invokeString)
        raise (OSError, """Could not find any %s programs.  You will need to install one,
    or customize %s to make it aware of yours.
    Looked for these programs:
    %s""" % (self.purpose, __file__, "\n".join([s[0] for s in self.softwareList])))
    #v2.4: %s""" % (self.purpose, __file__, "\n".join(s[0] for s in self.softwareList)))

softwareLists = {
    'diff/merge': [  
                    ('/usr/bin/meld',"%s %s %s"),
                    ('/usr/bin/kdiff3',"%s %s %s"),
                    (r'C:\Program Files\Araxis\Araxis Merge v6.5\Merge.exe','"%s" %s %s'),                
                    (r'C:\Program Files\TortoiseSVN\bin\TortoiseMerge.exe', '"%s" /base:"%s" /mine:"%s"'),
                    ('FileMerge','%s %s %s'),        
                    ('kompare','%s %s %s'),   
                    ('WinMerge','%s %s %s'),         
                    ('xxdiff','%s %s %s'),        
                    ('fldiff','%s %s %s'),
                    ('gtkdiff','%s %s %s'),        
                    ('tkdiff','%s %s %s'),         
                    ('gvimdiff','%s %s %s'),        
                    ('diff',"%s %s %s"),
                    (r'c:\windows\system32\comp.exe',"%s %s %s")],
    'text editor': [
        ('gedit', '%s %s'),
        ('textpad', '%s %s'),
        ('notepad.exe', '%s %s'),
        ('pico', '%s %s'),
        ('emacs', '%s %s'),
        ('vim', '%s %s'),
        ('vi', '%s %s'),
        ('ed', '%s %s'),
        ('edlin', '%s %s')
                   ]
}

diffMergeSearcher = SoftwareSearcher(softwareLists['diff/merge'],'diff/merge')
editSearcher = SoftwareSearcher(softwareLists['text editor'], 'text editor')
editor = os.environ.get('EDITOR')
if editor:
    editSearcher.find = lambda: (editor, "%s %s")

class CaselessDict(dict):
    """dict with case-insensitive keys.

    Posted to ASPN Python Cookbook by Jeff Donner - http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66315"""
    def __init__(self, other=None):
        if other:
            # Doesn't do keyword args
            if isinstance(other, dict):
                for k,v in other.items():
                    dict.__setitem__(self, k.lower(), v)
            else:
                for k,v in other:
                    dict.__setitem__(self, k.lower(), v)
    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())
    def __setitem__(self, key, value):
        dict.__setitem__(self, key.lower(), value)
    def __contains__(self, key):
        return dict.__contains__(self, key.lower())
    def has_key(self, key):
        return dict.has_key(self, key.lower())
    def get(self, key, def_val=None):
        return dict.get(self, key.lower(), def_val)
    def setdefault(self, key, def_val=None):
        return dict.setdefault(self, key.lower(), def_val)
    def update(self, other):
        for k,v in other.items():
            dict.__setitem__(self, k.lower(), v)
    def fromkeys(self, iterable, value=None):
        d = CaselessDict()
        for k in iterable:
            dict.__setitem__(d, k.lower(), value)
        return d
    def pop(self, key, def_val=None):
        return dict.pop(self, key.lower(), def_val)

class Parser(object):
    comment_def = "--" + pyparsing.ZeroOrMore(pyparsing.CharsNotIn("\n"))    
    def __init__(self, scanner, retainSeparator=True):
        self.scanner = scanner
        self.scanner.ignore(pyparsing.sglQuotedString)
        self.scanner.ignore(pyparsing.dblQuotedString)
        self.scanner.ignore(self.comment_def)
        self.scanner.ignore(pyparsing.cStyleComment)
        self.retainSeparator = retainSeparator
    def separate(self, txt):
        itms = []
        for (sqlcommand, start, end) in self.scanner.scanString(txt):
            if sqlcommand:
                if type(sqlcommand[0]) == pyparsing.ParseResults:
                    if self.retainSeparator:
                        itms.append("".join(sqlcommand[0]))
                    else:
                        itms.append(sqlcommand[0][0])
                else:
                    if sqlcommand[0]:
                        itms.append(sqlcommand[0])
        return itms

pipeSeparator = Parser(pyparsing.SkipTo((pyparsing.Literal('|') ^ pyparsing.StringEnd()), include=True), retainSeparator=False) 
bindScanner = Parser(pyparsing.Literal(':') + pyparsing.Word( pyparsing.alphanums + "_$#" ))
commandSeparator = Parser(pyparsing.SkipTo((pyparsing.Literal(';') ^ pyparsing.StringEnd()), include=True))

def findBinds(target, existingBinds, givenBindVars = {}):
    result = givenBindVars
    for finding, startat, endat in bindScanner.scanner.scanString(target):
        varname = finding[1]
        try:
            result[varname] = existingBinds[varname]
        except KeyError:
            if not givenBindVars.has_key(varname):
                print 'Bind variable %s not defined.' % (varname)                
    return result
        
class sqlpyPlus(sqlpython.sqlpython):
    defaultExtension = 'sql'
    shortcuts = {'?': 'help', '@': 'getrun', '!': 'shell', ':': 'setbind', '\\': 'psql'}    
    multilineCommands = '''select insert update delete tselect
        create drop alter'''.split()
    defaultFileName = 'afiedt.buf'
    def __init__(self):
        sqlpython.sqlpython.__init__(self)
        self.binds = CaselessDict()
        self.sqlBuffer = []
        self.settable = ['maxtselctrows', 'maxfetch', 'autobind', 'failover', 'timeout'] # settables must be lowercase
        self.stdoutBeforeSpool = sys.stdout
        self.spoolFile = None
        self.autobind = False
        self.failover = False
    def default(self, arg, do_everywhere=False):
        sqlpython.sqlpython.default(self, arg, do_everywhere)
        self.sqlBuffer.append(self.query)            

    # overrides cmd's parseline
    def parseline(self, line):
        """Parse the line into a command name and a string containing
        the arguments.  Returns a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.        
        Overrides cmd.cmd.parseline to accept variety of shortcuts.."""
        
        cmd, arg, line = sqlpython.sqlpython.parseline(self, line)
        if cmd in ('select', 'sleect', 'insert', 'update', 'delete', 'describe',
                          'desc', 'comments', 'pull', 'refs', 'desc', 'triggers', 'find') \
               and not hasattr(self, 'curs'):
            print 'Not connected.'
            return '', '', ''
        return cmd, arg, line
    
    def onecmd_plus_hooks(self, line):                          
        line = self.precmd(line)
        stop = self.onecmd(line)
        stop = self.postcmd(stop, line)

    def do_shortcuts(self,arg):
        """Lists available first-character shortcuts
        (i.e. '!dir' is equivalent to 'shell dir')"""
        for (scchar, scto) in self.shortcuts.items():
            print '%s: %s' % (scchar, scto)

    def colnames(self):
        return [d[0] for d in curs.description]

    def sql_format_itm(self, itm, needsquotes):
        if itm is None:
            return 'NULL'
        if needsquotes:
            return "'%s'" % str(itm)
        return str(itm)
    def output_as_insert_statements(self):
        usequotes = [d[1] != cx_Oracle.NUMBER for d in self.curs.description]
        def formatRow(row):
            return ','.join(self.sql_format_itm(itm, useq)
                            for (itm, useq) in zip(row, usequotes))
        result = ['INSERT INTO %s (%s) VALUES (%s);' %
                  (self.tblname, ','.join(self.colnames), formatRow(row))
                  for row in self.rows]
        return '\n'.join(result)
        
    def output_row_as_xml(self, row):
        result = ['  <%s>\n    %s\n  </%s>' %
                  (colname.lower(), str('' if (itm is None) else itm), colname.lower()) 
                  for (itm, colname) in zip(row, self.colnames)]
        return '\n'.join(result)        
    def output_as_xml(self):
        result = ['<%s>\n%s\n</%s>' %
                  (self.tblname, self.output_row_as_xml(row), self.tblname)
                  for row in self.rows]
        return '\n'.join(result)

    def output_as_html_table(self):
        result = ''.join('<th>%s</th>' % c for c in self.colnames)
        result = ['  <tr>\n    %s\n  </tr>' % result]
        for row in self.rows:
            result.append('  <tr>\n    %s\n  </tr>' %
                          (''.join('<td>%s</td>' %
                                   str('' if (itm is None) else itm)
                           for itm in row)))                
        result = '''<table id="%s">
%s
</table>''' % (self.tblname, '\n'.join(result))
        return result

    def output_as_list(self, align):
        result = []
        colnamelen = max(len(colname) for colname in self.colnames) + 1        
        for (idx, row) in enumerate(self.rows):
            result.append('\n**** Row: %d' % (idx+1))
            for (itm, colname) in zip(row, self.colnames):
                if align:
                    colname = colname.ljust(colnamelen)
                result.append('%s: %s' % (colname, itm))
        return '\n'.join(result)

    tableNameFinder = re.compile(r'from\s+([\w$#_"]+)', re.IGNORECASE | re.MULTILINE | re.DOTALL)          
    def output(self, outformat, rowlimit):
        self.tblname = self.tableNameFinder.search(self.curs.statement).group(1)
        self.colnames = [d[0] for d in self.curs.description]
        if outformat == '\\i':
            result = self.output_as_insert_statements()
        elif outformat ==  '\\x':
            result = self.output_as_xml()
        elif outformat == '\\g':
            result = self.output_as_list(align=False)
        elif outformat == '\\G':
            result = self.output_as_list(align=True)            
        elif outformat in ('\\s', '\\S', '\\c', '\\C'): #csv
            result = []
            if outformat in ('\\s', '\\c'):
                result.append(','.join('"%s"' % colname for colname in self.colnames))
            for row in self.rows:
                result.append(','.join('"%s"' % ('' if itm is None else itm) for itm in row))
            result = '\n'.join(result)
        elif outformat == '\\h':
            result = self.output_as_html_table()
        elif outformat == '\\t':
            rows = [self.colnames]
            rows.extend(list(self.rows))
            transpr = [[rows[y][x] for y in range(len(rows))]for x in range(len(rows[0]))] # matrix transpose
            newdesc = [['ROW N.'+str(y),10] for y in range(len(rows))]
            for x in range(len(self.curs.description)):
                if str(self.curs.description[x][1]) == "<type 'cx_Oracle.BINARY'>":  # handles RAW columns
                    rname = transpr[x][0]
                    transpr[x] = map(binascii.b2a_hex, transpr[x])
                    transpr[x][0] = rname
            newdesc[0][0] = 'COLUMN NAME'
            result = '\n' + sqlpython.pmatrix(transpr,newdesc)            
        else:
            result = sqlpython.pmatrix(self.rows, self.curs.description, self.maxfetch)
        return result
                        
    statementEndPattern = re.compile(r'(.*)(;|\\[gGhtxicCsS])\s*(\d*)$', re.DOTALL | re.MULTILINE)
    # what about quote-enclosed?
    
    def findTerminator(self, statement):
        m = self.statementEndPattern.search(statement)
        if m:
            return m.groups()
        else:
            return statement, None, None
    
    legalOracle = re.compile('[a-zA-Z_$#]')
    
    def do_select(self, arg, bindVarsIn=None, override_terminator=None):
        """Fetch rows from a table.
        
        Limit the number of rows retrieved by appending
        an integer after the terminator
        (example: SELECT * FROM mytable;10 )
        
        Output may be formatted by choosing an alternative terminator
        ("help terminators" for details)
        """
        bindVarsIn = bindVarsIn or {}
        self.query = 'select ' + arg
        (self.query, terminator, rowlimit) = self.findTerminator(self.query)
        if override_terminator:
            terminator = override_terminator
        rowlimit = int(rowlimit or 0)
        try:
            self.varsUsed = findBinds(self.query, self.binds, bindVarsIn)
            self.curs.execute(self.query, self.varsUsed)
            self.rows = self.curs.fetchmany(min(self.maxfetch, (rowlimit or self.maxfetch)))
            self.desc = self.curs.description
            self.rc = self.curs.rowcount
            if self.rc > 0:
                self.stdout.write('\n%s\n' % (self.output(terminator, rowlimit)))
            if self.rc == 0:
                print '\nNo rows Selected.\n'
            elif self.rc == 1: 
                print '\n1 row selected.\n'
                if self.autobind:
                    self.binds.update(dict(zip([''.join(l for l in d[0] if l.isalnum()) for d in self.desc], self.rows[0])))
                    if len(self.desc) == 1:
                        self.binds['_'] = self.rows[0][0]
            elif self.rc < self.maxfetch:
                print '\n%d rows selected.\n' % self.rc
            else:
                print '\nSelected Max Num rows (%d)' % self.rc
        except Exception, e:
            print e
            import traceback
            traceback.print_exc(file=sys.stdout)
        self.sqlBuffer.append(self.query)

    pullflags = flagReader.FlagSet([flagReader.Flag('full')])            
    def do_pull(self, arg):
        """Displays source code.
        
        --full, -f: get dependent objects as well"""
        
        options, arg = self.pullflags.parse(arg)
        object_type, owner, object_name = self.resolve(arg.strip(self.terminator).upper())
        self.stdout.write("%s %s.%s\n" % (object_type, owner, object_name))
        self.stdout.write(self.curs.callfunc('DBMS_METADATA.GET_DDL', cx_Oracle.CLOB,
                                 [object_type, object_name, owner])+'\n')
        if options.has_key('full'):
            for dependent_type in ('OBJECT_GRANT', 'CONSTRAINT', 'TRIGGER'):        
                try:
                    self.stdout.write(self.curs.callfunc('DBMS_METADATA.GET_DEPENDENT_DDL', cx_Oracle.CLOB,
                                          [dependent_type, object_name, owner])+'\n')
                except cx_Oracle.DatabaseError:
                    pass

    findflags = flagReader.FlagSet([flagReader.Flag('insensitive')])            
    def do_find(self, arg):
        """Finds argument in source code.
        
        --insensitive, -i: case-insensitive search"""

        options, arg = self.findflags.parse(arg)
        if options.has_key('insensitive'):
            searchfor = "LOWER(text)"
            arg = arg.lower()
        else:
            searchfor = "text"
        self.do_select("* from all_source where %s like '%%%s%%'" % (searchfor, arg))
        
    def do_describe(self, arg):
        "emulates SQL*Plus's DESCRIBE"
        object_type, owner, object_name = self.resolve(arg.strip(self.terminator).upper())
        self.stdout.write("%s %s.%s\n" % (object_type, owner, object_name))
        descQ = descQueries.get(object_type)
        if descQ:
            for q in descQ:
                self.do_select(q,bindVarsIn={'object_name':object_name, 'owner':owner})
        elif object_type == 'PACKAGE':
            self.curs.execute(descQueries['PackageObjects'][0], {'package_name':object_name, 'owner':owner})
            packageContents = self.curs.fetchall()
            for (packageObj_name,) in packageContents:
                print packageObj_name
                self.do_select(descQueries['PackageObjArgs'][0],bindVarsIn={'package_name':object_name, 'owner':owner, 'object_name':packageObj_name})
    do_desc = do_describe
    
    def do_comments(self, arg):
        'Prints comments on a table and its columns.'
        object_type, owner, object_name = self.resolve(arg.strip(self.terminator).upper())
        if object_type:
            self.curs.execute(queries['tabComments'],{'table_name':object_name, 'owner':owner})
            self.stdout.write("%s %s.%s: %s\n" % (object_type, owner, object_name, self.curs.fetchone()[0]))
            self.do_select(queries['colComments'],bindVarsIn={'owner':owner, 'object_name': object_name})

    def resolve(self, identifier):
        """Checks (my objects).name, (my synonyms).name, (public synonyms).name
        to resolve a database object's name. """
        parts = identifier.split('.')
        try:
            if len(parts) == 2:
                owner, object_name = parts
                self.curs.execute('SELECT object_type FROM all_objects WHERE owner = :owner AND object_name = :object_name',
                                  {'owner': owner, 'object_name': object_name})
                object_type = self.curs.fetchone()[0]
            elif len(parts) == 1:
                object_name = parts[0]
                self.curs.execute(queries['resolve'], {'objName':object_name})
                object_type, object_name, owner = self.curs.fetchone()
        except TypeError:
            print 'Could not resolve object %s.' % identifier
            object_type, owner, object_name = '', '', ''
        return object_type, owner, object_name

    def do_resolve(self, arg):
        self.stdout.write(self.resolve(arg)+'\n')
                          
    def spoolstop(self):
        if self.spoolFile:
            sys.stdout = self.stdoutBeforeSpool
            print 'Finished spooling to ', self.spoolFile.name
            self.spoolFile.close()
            self.spoolFile = None
    
    def do_spool(self, arg):
        """spool [filename] - begins redirecting output to FILENAME."""
        self.spoolstop()
        arg = arg.strip()
        if not arg:
            arg = 'output.lst'
        if arg.lower() != 'off':
            if '.' not in arg:
                arg = '%s.lst' % arg
            print 'Sending output to %s (until SPOOL OFF received)' % (arg)
            self.spoolFile = open(arg, 'w')
            sys.stdout = self.spoolFile

    def write(self, arg, fname): 
        originalOut = sys.stdout
        f = open(fname, 'w')
        sys.stdout = f
        self.onecmd_plus_hooks(arg)
        f.close()
        sys.stdout = originalOut
        
    def do_write(self, args):
        'write [filename.extension] query - writes result to a file'
        words = args.split(None, 1)
        if len(words) > 1 and '.' in words[0]:
            fname, command = words
        else:
            fname, command = 'output.txt', args
        self.write(command, fname)
        print 'Results written to %s' % os.path.join(os.getcwd(), fname)
        
    def do_compare(self, args):
        """COMPARE query1 TO query2 - uses external tool to display differences.
    
        Sorting is recommended to avoid false hits.
        Will attempt to use a graphical diff/merge tool like kdiff3, meld, or Araxis Merge, 
        if they are installed."""
        fnames = []
        args2 = args.split(' to ')
        for n in range(len(args2)):
            query = args2[n]
            fnames.append('compare%s.txt' % n)
            if query.rstrip()[-1] != self.terminator: 
                query = '%s%s' % (query, self.terminator)
            self.write(query, fnames[n])           
        diffMergeSearcher.invoke(fnames[0], fnames[1])

    bufferPosPattern = re.compile('\d+')
    rangeIndicators = ('-',':')

    def do_get(self, fname):
        'Brings SQL commands from a file to the in-memory SQL buffer.'
        numCommandsLoaded = self.load(fname)
        if numCommandsLoaded:
            self.do_list('%d -' % (len(self.history) - numCommandsLoaded))
    def do_getrun(self, fname):
        'Brings SQL commands from a file to the in-memory SQL buffer, and executes them.'
        numCommandsLoaded = self.do_load(fname) * -1
        if numCommandsLoaded:
            for command in self.history[numCommandsLoaded:]:
                self.onecmd_plus_hooks(command)
    def do_psql(self, arg):
        '''Shortcut commands emulating psql's backslash commands.
        
        \c connect
        \d desc
        \e edit
        \g run
        \h help
        \i getrun
        \o spool
        \p list
        \w save
        \db _dir_tablespaces
        \dd comments
        \dn _dir_schemas
        \dt _dir_tables
        \dv _dir_views
        \di _dir_indexes
        \? help psql'''
        commands = {}
        for c in self.do_psql.__doc__.splitlines()[2:]:
            (abbrev, command) = c.split(None, 1)
            commands[abbrev[1:]] = command
        words = arg.split(None,1)
        abbrev = words[0]
        try:
            args = words[1]
        except IndexError:
            args = ''
        try:
            self.onecmd('%s %s' % (commands[abbrev], args))
            self.onecmd('q')
        except KeyError:
            print 'psql command \%s not yet supported.' % abbrev
            
    def do__dir_tables(self, arg):
        self.do_select("""table_name, 'TABLE' as type, owner FROM all_tables WHERE table_name LIKE '%%%s%%'""" % arg.upper())        

    def do__dir_views(self, arg):
        self.do_select("""view_name, 'VIEW' as type, owner FROM all_views WHERE view_name LIKE '%%%s%%'""" % arg.upper()) 

    def do__dir_indexes(self, arg):
        self.do_select("""index_name, index_type, owner FROM all_indexes WHERE index_name LIKE '%%%s%%' OR table_name LIKE '%%%s%%'""" % (arg.upper(), arg.upper())) 

    def do__dir_tablespaces(self, arg):
        self.do_select("""tablespace_name, file_name from dba_data_files""") 

    def do__dir_schemas(self, arg):
        self.do_select("""owner, count(*) AS objects FROM all_objects GROUP BY owner ORDER BY owner""") 
        
    def do_head(self, arg):
        nrows = 10
        args = arg.split()
        if len(args) > 1:
            for a in args:
                if a[0] == '-':
                    try:
                        nrows = int(a[1:])
                        args.remove(a)
                    except:
                        pass
            arg = ' '.join(args)
        self.do_select('* from %s;%d' % (arg, nrows))
        
    def do_print(self, arg):
        'print VARNAME: Show current value of bind variable VARNAME.'
        if arg: 
            if arg[0] == ':':
                arg = arg[1:]
            try:
                self.stdout.write(self.binds[arg]+'\n')
            except KeyError:
                self.stdout.write('No bind variable %s\n' % arg)
        else:
            self.do_setbind('')
    def do_setbind(self, arg):
        args = arg.split(None, 2)
        if len(args) == 0:
            for (var, val) in self.binds.items():
                print ':%s = %s' % (var, val)
        elif len(args) == 1:
            try:
                print ':%s = %s' % (args[0], self.binds[args[0]])
            except KeyError, e:
                print noSuchBindMsg % args[0]
        elif len(args) > 2 and args[1] in ('=',':='):
            var, val = args[0], args[2]
            if val[0] == val[-1] == "'" and len(val) > 1:
                val = val[1:-1]
            self.binds[var] = val
        else:
            print 'Could not parse ', args            
    def do_exec(self, arg):
        if arg[0] == ':':
            self.do_setbind(arg[1:])
        else:
            self.default('exec %s' % arg)

    def do_cat(self, arg):
        targets = arg.split()
        for target in targets:
            self.do_select('* from %s' % target)
    
    def do_grep(self, arg):
        """grep PATTERN TABLE - search for term in any of TABLE's fields"""
        targets = arg.split()
        pattern = targets.pop(0)
        for target in targets:
            target = target.rstrip(';')
            sql = []
            try:
                self.curs.execute('select * from %s where 1=0' % target)
                sql = ' or '.join("%s LIKE '%%%s%%'" % (d[0], pattern) for d in self.curs.description)
                sql = '* FROM %s WHERE %s' % (target, sql)
                self.do_select(sql)
            except Exception, e:
                print e
                import traceback
                traceback.print_exc(file=sys.stdout)                

    def do_refs(self, arg):
        object_type, owner, object_name = self.resolve(arg.strip(self.terminator).upper())
        if object_type == 'TABLE':
            self.do_select(queries['refs'],bindVarsIn={'object_name':object_name, 'owner':owner})

def _test():
    import doctest
    doctest.testmod()
    
if __name__ == "__main__":
    "Silent return implies that all unit tests succeeded.  Use -v to see details."
    _test()