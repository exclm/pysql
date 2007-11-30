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
) ORDER BY priority ASC""",
'descTable': """
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
ORDER BY atc.column_id;""",
'PackageObjects':"""
SELECT DISTINCT object_name
FROM all_arguments
WHERE package_name = :package_name
AND      owner = :owner""",
'PackageObjArgs':"""
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
ORDER BY sequence""",
'descProcedure':"""
	     argument_name,	     
	     data_type,
	     in_out,
	     default_value
FROM all_arguments
WHERE object_name = :object_name
AND      owner = :owner
AND      package_name IS NULL
AND      argument_name IS NOT NULL
ORDER BY sequence;""",
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
}

import sys, os, re, sqlpython, cx_Oracle, pyparsing

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
    
class NotSettableError(Exception):
    None

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
    def __init__(self):
        sqlpython.sqlpython.__init__(self)
        self.binds = CaselessDict()
        self.sqlBuffer = []
        self.history = []
        self.settable = ['maxtselctrows', 'maxfetch', 'autobind', 'failover', 'timeout'] # settables must be lowercase
        self.stdoutBeforeSpool = sys.stdout
        self.spoolFile = None
        self.autobind = False
        self.failover = False
        self.singleline = '''desc describe'''.split()

    def default(self, arg, do_everywhere=False):
        sqlpython.sqlpython.default(self, arg, do_everywhere)
        self.sqlBuffer.append(self.query)            

    # overrides cmd's parseline
    shortcuts = {'?': 'help', '@': 'getrun', '!': 'shell', ':': 'setbind', '\\': 'psql'}
    def parseline(self, line):
        """Parse the line into a command name and a string containing
        the arguments.  Returns a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.	
        Overrides cmd.cmd.parseline to accept variety of shortcuts.."""
        line = line.strip()
        if not line:
            return None, None, line
        shortcut = self.shortcuts.get(line[0])
        if shortcut:
            cmd, arg = shortcut, line[1:].strip()
        else:
            i, n = 0, len(line)
            while i < n and line[i] in self.identchars: i = i+1
            cmd, arg = line[:i], line[i:].strip()
        if cmd.lower() in ('select', 'sleect', 'insert', 'update', 'delete', 'describe',
                          'desc', 'comments') \
            and not hasattr(self, 'curs'):
            print 'Not connected.'
            return '', '', ''
        return cmd, arg, line

    def precmd(self, line):
        """Hook method executed just before the command line is
        interpreted, but after the input prompt is generated and issued.
        Makes commands case-insensitive (but unfortunately does not alter command completion).
        """
        '''
        savestdout = sys.stdout
        pipefilename = 'sqlpython.pipeline.tmp'
        pipedCommands = pipeSeparator.separate(line)
        if len(pipedCommands) > 1:
            f = open(pipefilename,'w')
            sys.stdout = f
            self.precmd(pipedCommands[0])
            self.onecmd(pipedCommands[0])
            self.postcmd(False, pipedCommands[0])
            f.close()
            sys.stdout = savestdout
            os.system('%s < %s' % (pipedCommands[1], pipefilename))
        '''
        try:
            args = line.split(None,1)
            args[0] = args[0].lower()
            statement = ' '.join(args)            
            if args[0] not in self.singleline:
                statement = finishStatement(statement)
            return statement
        except Exception:
            return line
    
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
        print result
        print type(result)
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
        else:
            result = sqlpython.pmatrix(self.rows, self.curs.description, self.maxfetch)
        return result
                        
    def do_select(self, arg, bindVarsIn=None):
        """Fetch rows from a table.
        
        Limit the number of rows retrieved by appending
        an integer after the terminator
        (example: SELECT * FROM mytable;10 )
        
        Output may be formatted by choosing an alternative terminator
        ("help terminators" for details)
        """
        bindVarsIn = bindVarsIn or {}
        self.query = 'select ' + arg
        (self.query, terminator, rowlimit) = sqlpython.findTerminator(self.query)
        rowlimit = int(rowlimit or 0)
        if terminator == '\\t':
            self.do_tselect(' '.join(self.query.split()[1:]) + ';', rowlimit)
            return
        else:
            try:
                self.varsUsed = findBinds(self.query, self.binds, bindVarsIn)
                self.curs.execute(self.query, self.varsUsed)
                self.rows = self.curs.fetchmany(min(self.maxfetch, (stmt.rowlimit or self.maxfetch)))
                self.desc = self.curs.description
                self.rc = self.curs.rowcount
                if self.rc > 0:
                    print '\n' + self.output(outformat, rowlimit)
                if self.rc == 0:
                    print '\nNo rows Selected.\n'
                elif self.rc == 1: 
                    print '\n1 row selected.\n'
                    if self.autobind:
                        self.binds.update(dict(zip([d[0] for d in self.desc], self.rows[0])))
                elif self.rc < self.maxfetch:
                    print '\n%d rows selected.\n' % self.rc
                else:
                    print '\nSelected Max Num rows (%d)' % self.rc                 
            except Exception, e:
                print e
                import traceback
                traceback.print_exc(file=sys.stdout)
        self.sqlBuffer.append(self.query)

    def showParam(self, param):
        param = param.strip().lower()
        if param in self.settable:
            val = getattr(self, param)
            print '%s: %s' % (param, str(getattr(self, param)))

    def do_show(self, arg):
        'Shows value of a (sqlpython, not ORACLE) parameter'
        arg = arg.strip().lower()
        if arg:
            self.showParam(arg)
        else:
            for param in self.settable:
                self.showParam(param)

    def cast(self, current, new):
        typ = type(current)
        if typ == bool:
            new = new.lower()            
            try:
                if (new=='on') or (new[0] in ('y','t')):
                    return True
                return False
            except TypeError:
                None
        try:
            return typ(new)
        except:
            print "Problem setting parameter (now %s) to %s; incorrect type?" % (current, new)
            return current
    
    def do_set(self, arg):
        'Sets a (sqlpython, not ORACLE) parameter'        
        try:
            paramName, val = arg.split(None, 1)
        except Exception:
            self.do_show(arg)
            return
        paramName = paramName.lower()
        try:
            current = getattr(self, paramName)
            if callable(current):
                raise NotSettableError
        except (AttributeError, NotSettableError):
            self.fail('set %s' % arg)
            return
        val = self.cast(current, val.strip(';'))
        print paramName, ' - was: ', current
        setattr(self, paramName.lower(), val)
        print 'now: ', val
    
    def do_describe(self, arg):
        "emulates SQL*Plus's DESCRIBE"
        object_type, owner, object_name = self.resolve(arg.strip(self.terminator).upper())
        print "%s %s.%s" % (object_type, owner, object_name)
        if object_type in ('TABLE','VIEW'):
            self.do_select(queries['descTable'],{'object_name':object_name, 'owner':owner})
        elif object_type == 'PACKAGE':
            self.curs.execute(queries['PackageObjects'], {'package_name':object_name, 'owner':owner})
            for (packageObj_name,) in self.curs:
                print packageObj_name
                self.do_select(queries['PackageObjArgs'],{'package_name':object_name, 'owner':owner, 'object_name':packageObj_name})
        else:
            self.do_select(queries['descProcedure'],{'owner':owner, 'object_name':object_name})
    do_desc = do_describe
    
    def do_comments(self, arg):
        'Prints comments on a table and its columns.'
        object_type, owner, object_name = self.resolve(arg.strip(self.terminator).upper())
        if object_type:
            self.curs.execute(queries['tabComments'],{'table_name':object_name, 'owner':owner})
            print "%s %s.%s: %s" % (object_type, owner, object_name, self.curs.fetchone()[0])
            self.do_select(queries['colComments'],{'owner':owner, 'object_name': object_name})

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

    def do_shell(self, arg):
        'execute a command as if at the OS prompt.'
        os.system(arg)
        
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
        self.onecmd(arg)
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
    
        Sorting is recommended to avoid false hits."""
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
    def bufferPositions(self, arg):
        if not self.sqlBuffer:
            return []
        arg = arg.strip(self.terminator)
        arg = arg.strip()
        if not arg:
            return [0]
        arg = arg.strip().lower()
        if arg in ('*', 'all', '-', ':'):
            return range(len(self.sqlBuffer))

        edges = [e for e in self.bufferPosPattern.findall(arg)]
        edges = [int(e) for e in edges]
        if len(edges) > 1:
            edges = edges[:2]
        else:
            if arg[0] in self.rangeIndicators or arg[-1] in self.rangeIndicators:
                edges.append(0)
        edges.sort()
        start = max(edges[0], 0)
        end = min(edges[-1], len(self.sqlBuffer)-1)
        return range(start, end+1)
    def do_run(self, arg):
        'run [N]: runs the SQL that was run N commands ago'	
        for pos in self.bufferPositions(arg):
            self.onecmd(self.sqlBuffer[-1-pos])
    def do_history(self, arg):
        for (i, itm) in enumerate(self.history):
            print '-------------------------[%d]' % (i+1)
            print itm
    def do_list(self, arg):
        'list [N]: lists the SQL that was run N commands ago'
        for pos in self.bufferPositions(arg):
            print '*** %i statements ago ***' % pos
            print self.sqlBuffer[-1-pos]
    def load(self, fname):
        """Pulls command(s) into sql buffer.  Returns number of commands loaded."""
        initialLength = len(self.sqlBuffer)
        try:
            f = open(fname, 'r')
        except IOError, e:
            try:
                f = open('%s.sql' % fname, 'r')
            except:
                print 'Problem opening file %s: \n%s' % (fname, e)
                return 0
        txt = f.read()
        f.close()
        self.sqlBuffer.extend(commandSeparator.separate(txt))                           
        return len(self.sqlBuffer) - initialLength
    def do_ed(self, arg):
        'ed [N]: brings up SQL from N commands ago in text editor, and puts result in SQL buffer.'
        fname = 'mysqlpy_temp.sql'
        try:
            buffer = self.sqlBuffer[-1 - (int(arg or 0))]
        except IndexError:
            buffer = ''
        f = open(fname, 'w')
        f.write(buffer)
        f.close()
        editSearcher.invoke(fname)
        self.load(fname)
    do_edit = do_ed
    def do_get(self, fname):
        'Brings SQL commands from a file to the in-memory SQL buffer.'
        commandsLoaded = self.load(fname)
        if commandsLoaded:
            self.do_list('1-%d' % (commandsLoaded-1))
    def do_getrun(self, fname):
        'Brings SQL commands from a file to the in-memory SQL buffer, and executes them.'
        commandNums = range(self.load(fname))
        commandNums.reverse()
        for commandNum in commandNums:
            self.do_run(str(commandNum))
            self.sqlBuffer.pop()
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
    def do_save(self, fname):
        'save FILENAME: Saves most recent SQL command to disk.'
        f = open(fname, 'w')
        f.write(self.sqlBuffer[-1])
        f.close()
        
    def do_print(self, arg):
        'print VARNAME: Show current value of bind variable VARNAME.'
        if arg:
            if arg[0] == ':':
                arg = arg[1:]
            try:
                print self.binds[arg]
            except KeyError:
                print 'No bind variable ', arg
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
            
def _test():
    import doctest
    doctest.testmod()
    
if __name__ == "__main__":
    "Silent return implies that all unit tests succeeded.  Use -v to see details."
    _test()