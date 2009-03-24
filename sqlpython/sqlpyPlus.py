"""sqlpyPlus - extra features (inspired	 by Oracle SQL*Plus) for Luca Canali's sqlpython.py

Features include:
 - SQL*Plus-style bind variables
 - `set autobind on` stores single-line result sets in bind variables automatically
 - SQL buffer with list, run, ed, get, etc.; unlike SQL*Plus, buffer stores session's full history
 - @script.sql loads and runs (like SQL*Plus)
 - ! runs operating-system command
 - show and set to control sqlpython parameters
 - SQL*Plus-style describe, spool
 - write sends query result directly to file
 - comments shows table and column comments
 - compare ... to ... graphically compares results of two queries
 - commands are case-insensitive
 - context-sensitive tab-completion for table names, column names, etc.

Use 'help' within sqlpython for details.

Set bind variables the hard (SQL*Plus) way
exec :b = 3
or with a python-like shorthand
:b = 3

- catherinedevlin.blogspot.com  May 31, 2006
"""
import sys, os, re, sqlpython, cx_Oracle, pyparsing, re, completion, datetime, pickle, binascii, subprocess
from cmd2 import Cmd, make_option, options, Statekeeper, Cmd2TestCase
from output_templates import output_templates
from plothandler import Plot
try:
    import pylab
except (RuntimeError, ImportError):
    pass

descQueries = {
'TABLE': {
    True: # long description
("""
SELECT atc.column_id "#",
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
data_type,
acc.comments
FROM all_tab_columns atc
JOIN all_col_comments acc ON (acc.owner = atc.owner AND acc.table_name = atc.table_name AND acc.column_name = atc.column_name)
WHERE atc.table_name = :object_name
AND      atc.owner = :owner
ORDER BY atc.column_id;""",),
    None: # short description
("""
SELECT atc.column_name,
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
ORDER BY atc.column_id;""",)
}
          ,

'PROCEDURE': ("""
SELECT NVL(argument_name, 'Return Value') argument_name,             
data_type,
in_out,
default_value
FROM all_arguments
WHERE object_name = :object_name
AND      owner = :owner
AND      package_name IS NULL
ORDER BY sequence;""",),    
'PackageObjects':("""
SELECT DISTINCT object_name
FROM all_arguments
WHERE package_name = :package_name
AND      owner = :owner""",),
'PackageObjArgs':("""
SELECT object_name,
argument_name,             
data_type,
in_out,
default_value
FROM all_arguments
WHERE package_name = :package_name
AND      object_name = :object_name
AND      owner = :owner
AND      argument_name IS NOT NULL
ORDER BY sequence;""",),
'TRIGGER':("""
SELECT description
FROM   all_triggers
WHERE  owner = :owner
AND    trigger_name = :object_name;
""",
"""
SELECT table_owner,
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
SELECT index_type,
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
) ORDER BY priority ASC,
           length(object_type) ASC,
           object_type DESC""", # preference: PACKAGE before PACKAGE BODY, TABLE before INDEX
'tabComments': """
SELECT comments
FROM    all_tab_comments
WHERE owner = :owner
AND      table_name = :table_name""",
'colComments': """
SELECT
atc.column_name,
acc.comments             
FROM all_tab_columns atc
JOIN all_col_comments acc ON (atc.owner = acc.owner and atc.table_name = acc.table_name and atc.column_name = acc.column_name)
WHERE atc.table_name = :object_name
AND      atc.owner = :owner
ORDER BY atc.column_id;""",
'oneColComments': """
SELECTatc.column_name,
acc.comments             
FROM all_tab_columns atc
JOIN all_col_comments acc ON (atc.owner = acc.owner and atc.table_name = acc.table_name and atc.column_name = acc.column_name)
WHERE atc.table_name = :object_name
AND      atc.owner = :owner
AND      acc.column_name = :column_name
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
        try:
            key = key.lower()
        except AttributeError:
            pass
        dict.__setitem__(self, key, value)
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
    comment_def = "--" + ~ ('-' + pyparsing.CaselessKeyword('begin')) + pyparsing.ZeroOrMore(pyparsing.CharsNotIn("\n"))    
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

bindScanner = Parser(pyparsing.Literal(':') + pyparsing.Word( pyparsing.alphanums + "_$#" ))   
    
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

class ResultSet(list):
    pass

class Result(tuple):
    def __str__(self):
        return '\n'.join('%s: %s' % (colname, self[idx]) 
                         for (idx, colname) in enumerate(self.resultset.colnames))
    def __getattr__(self, attr):
        attr = attr.lower()
        try:
            return self[self.resultset.colnames.index(attr)]
        except ValueError:
            if attr in ('colnames', 'statement', 'bindvars'):
                return getattr(self.resultset, attr)
            else:
                raise AttributeError, "available columns are: " + ", ".join(self.resultset.colnames)      
    def bind(self):
        for (idx, colname) in enumerate(self.resultset.colnames):
            self.resultset.pystate['binds'][colname] = self[idx]
            self.resultset.pystate['binds'][str(idx+1)] = self[idx]
              
def centeredSlice(lst, center=0, width=1):
    width = max(width, -1)
    if center < 0:
        end = center + width + 1
        if end >= 0:
            end = None
        return lst[center-width:end]
    else:
        return lst[max(center-width,0):center+width+1] 
    
class sqlpyPlus(sqlpython.sqlpython):
    defaultExtension = 'sql'
    abbrev = True    
    sqlpython.sqlpython.shortcuts.update({':': 'setbind', 
                                          '\\': 'psql', 
                                          '@': 'get'})
    multilineCommands = '''select insert update delete tselect
                      create drop alter _multiline_comment'''.split()
    sqlpython.sqlpython.noSpecialParse.append('spool')
    commentGrammars = pyparsing.Or([pyparsing.Literal('--') + pyparsing.restOfLine, pyparsing.cStyleComment])
    commentGrammars = pyparsing.Or([Parser.comment_def, pyparsing.cStyleComment])
    prefixParser = pyparsing.Optional(pyparsing.Word(pyparsing.nums)('connection_number') 
                                      + ':')
    default_file_name = 'afiedt.buf'
    def __init__(self):
        sqlpython.sqlpython.__init__(self)
        self.binds = CaselessDict()
        self.settable += 'autobind commit_on_exit maxfetch maxtselctrows scan serveroutput sql_echo store_results timeout heading wildsql'.split()
        self.settable.remove('case_insensitive')
        self.settable.sort()
        self.stdoutBeforeSpool = sys.stdout
        self.sql_echo = False
        self.spoolFile = None
        self.autobind = False
        self.heading = True
        self.wildsql = False
        self.serveroutput = True
        self.scan = True
        self.nonpythoncommand = 'sql'
        self.substvars = {}
        self.result_history = []
        self.store_results = True
        self.pystate = {'r': [], 'binds': self.binds, 'substs': self.substvars}
        
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

    def dbms_output(self):
        "Dumps contents of Oracle's DBMS_OUTPUT buffer (where PUT_LINE goes)"
        try:
            line = self.curs.var(cx_Oracle.STRING)
            status = self.curs.var(cx_Oracle.NUMBER)
            self.curs.callproc('dbms_output.get_line', [line, status])
            while not status.getvalue():
                self.stdout.write(line.getvalue())
                self.stdout.write('\n')
                self.curs.callproc('dbms_output.get_line', [line, status])
        except AttributeError:
            pass
        
    def postcmd(self, stop, line):
        """Hook method executed just after a command dispatch is finished."""        
        if self.serveroutput:
            self.dbms_output()
        return stop
    
    def do_remark(self, line):
        '''
        REMARK is one way to denote a comment in SQL*Plus.
        
        Wrapping a *single* SQL or PL/SQL statement in `REMARK BEGIN` and `REMARK END`
        tells sqlpython to submit the enclosed code directly to Oracle as a single
        unit of code.  
        
        Without these markers, sqlpython fails to properly distinguish the beginning
        and end of all but the simplest PL/SQL blocks, causing errors.  sqlpython also
        slows down when parsing long SQL statements as it tries to determine whether
        the statement has ended yet; `REMARK BEGIN` and `REMARK END` allow it to skip this
        parsing.
        
        Standard SQL*Plus interprets REMARK BEGIN and REMARK END as comments, so it is
        safe to include them in SQL*Plus scripts.
        '''
        if not line.lower().strip().startswith('begin'):
            return
        statement = []
        next = self.pseudo_raw_input(self.continuation_prompt)
        while next.lower().split()[:2] != ['remark','end']:
            statement.append(next)
            next = self.pseudo_raw_input(self.continuation_prompt)
        return self.onecmd('\n'.join(statement))        

    def do_py(self, arg):
        '''
        py <command>: Executes a Python command.
        py: Enters interactive Python mode.
        End with `Ctrl-D` (Unix) / `Ctrl-Z` (Windows), `quit()`, 'exit()`.        
        Past SELECT results are exposed as list `r`; 
            most recent resultset is `r[-1]`.
        SQL bind, substitution variables are exposed as `binds`, `substs`.
        SQL and sqlpython commands can be issued with `sql("your command")`.
        '''
        return Cmd.do_py(self, arg)

    def do_get(self, args):
        """
        `get {script.sql}` or `@{script.sql}` runs the command(s) in {script.sql}.
        If additional arguments are supplied, they are assigned to &1, &2, etc.
        """        
        fname, args = args.split()[0], args.split()[1:]
        for (idx, arg) in enumerate(args):
            self.substvars[str(idx+1)] = arg
        return Cmd.do__load(self, fname)
    
    def onecmd_plus_hooks(self, line):                          
        line = self.precmd(line)
        stop = self.onecmd(line)
        stop = self.postcmd(stop, line)

    def _onchange_serveroutput(self, old, new):
        if new:
            self.curs.callproc('dbms_output.enable', [])        
        else:
            self.curs.callproc('dbms_output.disable', [])        
        
    def do_shortcuts(self,arg):
        """Lists available first-character shortcuts
        (i.e. '!dir' is equivalent to 'shell dir')"""
        for (scchar, scto) in self.shortcuts.items():
            print '%s: %s' % (scchar, scto)

    tableNameFinder = re.compile(r'from\s+([\w$#_"]+)', re.IGNORECASE | re.MULTILINE | re.DOTALL)          
    inputStatementFormatters = {
        cx_Oracle.STRING: "'%s'",
        cx_Oracle.DATETIME: "TO_DATE('%s', 'YYYY-MM-DD HH24:MI:SS')"}
    inputStatementFormatters[cx_Oracle.CLOB] = inputStatementFormatters[cx_Oracle.STRING]
    inputStatementFormatters[cx_Oracle.TIMESTAMP] = inputStatementFormatters[cx_Oracle.DATETIME]                
    def output(self, outformat, rowlimit):
        self.tblname = self.tableNameFinder.search(self.curs.statement).group(1)
        self.colnames = [d[0] for d in self.curs.description]
        if outformat in output_templates:
            self.colnamelen = max(len(colname) for colname in self.colnames)
            self.coltypes = [d[1] for d in self.curs.description]
            self.formatters = [self.inputStatementFormatters.get(typ, '%s') for typ in self.coltypes]    
            result = output_templates[outformat].generate(**self.__dict__)        
        elif outformat == '\\t': # transposed
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
        elif outformat in ('\\l', '\\L', '\\p', '\\b'):
            plot = Plot()
            plot.build(self, outformat)
            plot.shelve()                
            plot.draw()
            return ''
        else:
            result = sqlpython.pmatrix(self.rows, self.curs.description, self.maxfetch, heading=self.heading)
        return result
        
    legalOracle = re.compile('[a-zA-Z_$#]')

    def select_scalar_list(self, sql, binds={}):
        self._execute(sql, binds)
        return [r[0] for r in self.curs.fetchall()]
    
    columnNameRegex = re.compile(
        r'select\s+(.*)from',
        re.IGNORECASE | re.DOTALL | re.MULTILINE)        
    def completedefault(self, text, line, begidx, endidx):
        segment = completion.whichSegment(line)
        text = text.upper()
        completions = []
        if segment == 'select':
            stmt = "SELECT column_name FROM user_tab_columns WHERE column_name LIKE '%s%%'"
            completions = self.select_scalar_list(stmt % (text))
            if not completions:
                stmt = "SELECT column_name FROM all_tab_columns WHERE column_name LIKE '%s%%'"            
                completions = self.select_scalar_list(stmt % (text))
        if segment == 'from':
            columnNames = self.columnNameRegex.search(line)
            if columnNames:
                columnNames = columnNames.group(1)
                columnNames = [c.strip().upper() for c in columnNames.split(',')]
                stmt1 = "SELECT table_name FROM all_tab_columns WHERE column_name = '%s' AND table_name LIKE '%s%%'"
                for columnName in columnNames:
                    # and if columnName is * ?
                    completions.extend(self.select_scalar_list(stmt1 % (columnName, text)))                    
        if segment in ('from', 'update', 'insert into') and (not completions):
            stmt = "SELECT table_name FROM user_tables WHERE table_name LIKE '%s%%'"
            completions = self.select_scalar_list(stmt % (text))
            if not completions:
                stmt = """SELECT table_name FROM user_tables WHERE table_name LIKE '%s%%'
                      UNION
                      SELECT DISTINCT owner FROM all_tables WHERE owner LIKE '%%%s'"""
                completions = self.select_scalar_list(stmt % (text, text))
        if segment in ('where', 'group by', 'order by', 'having', 'set'):
            tableNames = completion.tableNamesFromFromClause(line)
            if tableNames:
                stmt = """SELECT column_name FROM all_tab_columns
                          WHERE table_name IN (%s)""" % \
                       (','.join("'%s'" % (t) for t in tableNames))
            stmt = "%s AND column_name LIKE '%s%%'" % (stmt, text)
            completions = self.select_scalar_list(stmt)
        if not segment:
            stmt = "SELECT object_name FROM all_objects WHERE object_name LIKE '%s%%'"
            completions = self.select_scalar_list(stmt % (text))
        return completions

    columnlistPattern = pyparsing.SkipTo(pyparsing.CaselessKeyword('from'))('columns') + \
                        pyparsing.SkipTo(pyparsing.stringEnd)('remainder')

    negator = pyparsing.Literal('!')('exclude')
    colNumber = pyparsing.Optional(negator) + pyparsing.Literal('#') + pyparsing.Word('-' + pyparsing.nums, pyparsing.nums)('column_number')
    colName = negator + pyparsing.Word('$_#' + pyparsing.alphas, '$_#' + pyparsing.alphanums)('column_name')
    wildColName = pyparsing.Optional(negator) + pyparsing.Word('?*%$_#' + pyparsing.alphas, '?*%$_#' + pyparsing.alphanums, min=2)('column_name')
    colNumber.ignore(pyparsing.cStyleComment).ignore(Parser.comment_def). \
              ignore(pyparsing.sglQuotedString).ignore(pyparsing.dblQuotedString) 
    wildSqlParser = colNumber ^ colName ^ wildColName
    wildSqlParser.ignore(pyparsing.cStyleComment).ignore(Parser.comment_def). \
                  ignore(pyparsing.sglQuotedString).ignore(pyparsing.dblQuotedString)   
    emptyCommaRegex = re.compile(',\s*,', re.DOTALL)
    deadStarterCommaRegex = re.compile('^\s*,', re.DOTALL)
    deadEnderCommaRegex = re.compile(',\s*$', re.DOTALL)    
    def expandWildSql(self, arg):
        try:
            columnlist = self.columnlistPattern.parseString(arg)
        except pyparsing.ParseException:
            return arg
        parseresults = list(self.wildSqlParser.scanString(columnlist.columns))
        # I would rather exclude non-wild column names in the grammar,
        # but can't figure out how
        parseresults = [p for p in parseresults if 
                        p[0].column_number or 
                        '*' in p[0].column_name or
                        '%' in p[0].column_name or
                        '?' in p[0].column_name or                        
                        p[0].exclude]
        if not parseresults:
            return arg       
        self.curs.execute('select * ' + columnlist.remainder, self.varsUsed)
        columns_available = [d[0] for d in self.curs.description]        
        replacers = {}
        included = set()
        excluded = set()        
        for (col, startpos, endpos) in parseresults:
            replacers[arg[startpos:endpos]] = []            
            if col.column_name:
                finder = col.column_name.replace('*','.*')
                finder = finder.replace('%','.*')
                finder = finder.replace('?','.')
                colnames = [c for c in columns_available if re.match(finder + '$', c, re.IGNORECASE)]
            elif col.column_number:
                idx = int(col.column_number)
                if idx > 0:
                    idx -= 1                
                colnames = [columns_available[idx]]
            if not colnames:
                print 'No columns found matching criteria.'
                return 'null from dual'
            for colname in colnames:
                if col.exclude:
                    included.discard(colname)
                    include_here = columns_available[:]
                    include_here.remove(colname)
                    replacers[arg[startpos:endpos]].extend(i for i in include_here if i not in replacers[arg[startpos:endpos]])
                    excluded.add(colname)
                else:
                    excluded.discard(colname)
                    replacers[arg[startpos:endpos]].append(colname)
                    
        replacers = sorted(replacers.items(), key=len, reverse=True)
        result = columnlist.columns
        for (target, replacement) in replacers:
            cols = [r for r in replacement if r not in excluded and r not in included]            
            replacement = ', '.join(cols)
            included.update(cols)
            result = result.replace(target, replacement)
        # some column names could get wiped out completely, so we fix their dangling commas
        result = self.emptyCommaRegex.sub(',', result)
        result = self.deadStarterCommaRegex.sub('', result)
        result = self.deadEnderCommaRegex.sub('', result)
        if not result.strip():
            print 'No columns found matching criteria.'
            return 'null from dual'        
        return result + ' ' + columnlist.remainder

    def do_prompt(self, args):
        print args
        
    def do_accept(self, args):
        try:
            prompt = args[args.lower().index('prompt ')+7:]
        except ValueError:
            prompt = ''
        varname = args.lower().split()[0]
        self.substvars[varname] = self.pseudo_raw_input(prompt)
                
    def ampersand_substitution(self, raw, regexpr, isglobal):
        subst = regexpr.search(raw)
        while subst:
            fullexpr, var = subst.group(1), subst.group(2)
            print 'Substitution variable %s found in:' % fullexpr
            print raw[max(subst.start()-20, 0):subst.end()+20]
            if var in self.substvars:
                val = self.substvars[var]
            else:
                val = raw_input('Substitution for %s (SET SCAN OFF to halt substitution): ' % fullexpr)
                if val.lower().split() == ['set','scan','off']:
                    self.scan = False
                    return raw
                if isglobal:
                    self.substvars[var] = val                
            raw = raw.replace(fullexpr, val)
            print 'Substituted %s for %s' % (val, fullexpr)
            subst = regexpr.search(raw) # do not FINDALL b/c we don't want to ask twice
        return raw

    numericampre = re.compile('(&(\d+))')    
    doubleampre = re.compile('(&&([a-zA-Z\d_$#]+))', re.IGNORECASE)
    singleampre = re.compile( '(&([a-zA-Z\d_$#]+))', re.IGNORECASE)
    def preparse(self, raw, **kwargs):
        if self.scan:
            raw = self.ampersand_substitution(raw, regexpr=self.numericampre, isglobal=False)
        if self.scan:
            raw = self.ampersand_substitution(raw, regexpr=self.doubleampre, isglobal=True)
        if self.scan:
            raw = self.ampersand_substitution(raw, regexpr=self.singleampre, isglobal=False)
        return raw
    
    rowlimitPattern = pyparsing.Word(pyparsing.nums)('rowlimit')
    terminators = '; \\C \\t \\i \\p \\l \\L \\b '.split() + output_templates.keys()

    @options([make_option('-r', '--row', type="int", default=-1,
                          help='Bind row #ROW instead of final row (zero-based)')])    
    def do_bind(self, arg=None, opts={}):
        '''
        Inserts the results from the final row in the last completed SELECT statement
        into bind variables with names corresponding to the column names.  When the optional 
        `autobind` setting is on, this will be issued automatically after every query that 
        returns exactly one row.
        '''
        try:
            self.pystate['r'][-1][opts.row].bind()
        except IndexError:
            print self.do_bind.__doc__
        
    def do_select(self, arg, bindVarsIn=None, terminator=None):
        """Fetch rows from a table.

        Limit the number of rows retrieved by appending
        an integer after the terminator
        (example: SELECT * FROM mytable;10 )

        Output may be formatted by choosing an alternative terminator
        ("help terminators" for details)
        """
        bindVarsIn = bindVarsIn or {}
        try:
            rowlimit = int(arg.parsed.suffix or 0)
        except ValueError:
            rowlimit = 0
            print "Specify desired number of rows after terminator (not '%s')" % arg.parsed.suffix
        if arg.parsed.terminator == '\\t':
            rowlimit = rowlimit or self.maxtselctrows
        self.varsUsed = findBinds(arg, self.binds, bindVarsIn)
        if self.wildsql:
            selecttext = self.expandWildSql(arg)
        else:
            selecttext = arg
        self.curs.execute('select ' + selecttext, self.varsUsed)
        self.rows = self.curs.fetchmany(min(self.maxfetch, (rowlimit or self.maxfetch)))
        self.rc = self.curs.rowcount
        if self.rc > 0:
            resultset = ResultSet()
            resultset.colnames = [d[0].lower() for d in self.curs.description]
            resultset.pystate = self.pystate
            resultset.statement = 'select ' + selecttext
            resultset.varsUsed = self.varsUsed
            resultset.extend([Result(r) for r in self.rows])
            for row in resultset:
                row.resultset = resultset
            self.pystate['r'].append(resultset)
            self.stdout.write('\n%s\n' % (self.output(arg.parsed.terminator, rowlimit)))
        if self.rc == 0:
            print '\nNo rows Selected.\n'
        elif self.rc == 1: 
            print '\n1 row selected.\n'
            if self.autobind:
                self.do_bind()
        elif self.rc < self.maxfetch:
            print '\n%d rows selected.\n' % self.rc
        else:
            print '\nSelected Max Num rows (%d)' % self.rc
        
    def do_cat(self, arg):
        '''Shortcut for SELECT * FROM'''
        return self.do_select(self.parsed('SELECT * FROM %s;' % arg, 
                                          terminator = arg.parsed.terminator or ';', 
                                          suffix = arg.parsed.suffix))

    def _pull(self, arg, opts, vc=None):
        """Displays source code."""
        if opts.dump:
            statekeeper = Statekeeper(self, ('stdout',))                        
        try:
            for (owner, object_type, object_name) in self.resolve_many(arg, opts):  
                if object_type in self.supported_ddl_types:
                    object_type = {'DATABASE LINK': 'DB_LINK', 'JAVA CLASS': 'JAVA_SOURCE'
                                   }.get(object_type) or object_type
                    object_type = object_type.replace(' ', '_')
                    if opts.dump:
                        try:
                            os.makedirs(os.path.join(owner.lower(), object_type.lower()))
                        except OSError:
                            pass
                        filename = os.path.join(owner.lower(), object_type.lower(), '%s.sql' % object_name.lower())
                        self.stdout = open(filename, 'w')
                        if vc:
                            subprocess.call(vc + [filename])
                    if object_type == 'PACKAGE':
                        ddl = [['PACKAGE_SPEC', object_name, owner],['PACKAGE_BODY', object_name, owner]]                            
                    elif object_type in ['CONTEXT', 'DIRECTORY', 'JOB']:
                        ddl = [[object_type, object_name]]
                    else:
                        ddl = [[object_type, object_name, owner]]
                    for ddlargs in ddl:
                        try:
                            code = str(self.curs.callfunc('DBMS_METADATA.GET_DDL', cx_Oracle.CLOB, ddlargs))
                            if opts.lines:
                                code = code.splitlines()
                                template = "%%-%dd:%%s" % len(str(len(code)))
                                code = '\n'.join(template % (n+1, line) for (n, line) in enumerate(code))
                            if opts.num is not None:
                                code = code.splitlines()
                                code = centeredSlice(code, center=opts.num+1, width=opts.width)
                                code = '\n'.join(code)
                            self.stdout.write('REMARK BEGIN %s\n%s\nREMARK END\n\n' % (object_name, code))
                        except cx_Oracle.DatabaseError, errmsg:
                            if object_type == 'JOB':
                                print '%s: DBMS_METADATA.GET_DDL does not support JOBs (MetaLink DocID 567504.1)' % object_name
                            elif 'ORA-31603' in str(errmsg): # not found, as in package w/o package body
                                pass
                            else:
                                raise
                    if opts.full:
                        for dependent_type in ('OBJECT_GRANT', 'CONSTRAINT', 'TRIGGER'):        
                            try:
                                self.stdout.write('REMARK BEGIN\n%s\nREMARK END\n\n' % str(self.curs.callfunc('DBMS_METADATA.GET_DEPENDENT_DDL', cx_Oracle.CLOB,
                                                                         [dependent_type, object_name, owner])))
                            except cx_Oracle.DatabaseError:
                                pass
                    if opts.dump:
                        self.stdout.close()
        except:
            if opts.dump:
                statekeeper.restore()
            raise
        if opts.dump:
            statekeeper.restore()    

    def do_show(self, arg):
        '''
        show                  - display value of all sqlpython parameters
        show (parameter name) - display value of a sqlpython parameter
        show parameter (parameter name) - display value of an ORACLE parameter
        show err (object type/name)     - errors from latest PL/SQL object compilation.
        show all err (type/name)        - all compilation errors from the user's PL/SQL objects.
        '''
        if arg.startswith('param'):
            try:
                paramname = arg.split()[1].lower()
            except IndexError:
                paramname = ''
            self.onecmd("""SELECT name, 
                           CASE type WHEN 1 THEN 'BOOLEAN'
                                     WHEN 2 THEN 'STRING'
                                     WHEN 3 THEN 'INTEGER'
                                     WHEN 4 THEN 'PARAMETER FILE'
                                     WHEN 5 THEN 'RESERVED'
                                     WHEN 6 THEN 'BIG INTEGER' END type, 
                           value FROM v$parameter WHERE name LIKE '%%%s%%';""" % paramname)
        else:
            argpieces = arg.lower().split()
            try:
                if argpieces[0][:3] == 'err':
                    return self._show_errors(all_users=False, limit=1, targets=argpieces[1:])
                elif (argpieces[0], argpieces[1][:3]) == ('all','err'):
                    return self._show_errors(all_users=False, limit=None, targets=argpieces[2:])
            except IndexError:
                pass
            return Cmd.do_show(self, arg)
            
    @options([make_option('-d', '--dump', action='store_true', help='dump results to files'),
              make_option('-f', '--full', action='store_true', help='get dependent objects as well'),
              make_option('-l', '--lines', action='store_true', help='print line numbers'),
              make_option('-n', '--num', type='int', help='only code near line #num'),
              make_option('-w', '--width', type='int', default=5, 
                          help='# of lines before and after --lineNo'),              
              make_option('-a', '--all', action='store_true', help="all schemas' objects"),
              make_option('-x', '--exact', action='store_true', help="match object name exactly")])
    def do_pull(self, arg, opts):
        """Displays source code."""
        self._pull(arg, opts)
            
    supported_ddl_types = 'CLUSTER, CONTEXT, DATABASE LINK, DIRECTORY, FUNCTION, INDEX, JOB, LIBRARY, MATERIALIZED VIEW, PACKAGE, PACKAGE BODY, PACKAGE SPEC, OPERATOR, PACKAGE, PROCEDURE, SEQUENCE, SYNONYM, TABLE, TRIGGER, VIEW, TYPE, TYPE BODY, XML SCHEMA'
    do_pull.__doc__ += '\n\nSupported DDL types: ' + supported_ddl_types
    supported_ddl_types = supported_ddl_types.split(', ')    

    def _vc(self, arg, opts, program):
        if not os.path.exists('.%s' % program):
            create = raw_input('%s repository not yet in current directory (%s).  Create (y/N)? ' % 
                               (program, os.getcwd()))
            if not create.strip().lower().startswith('y'):
                return
        subprocess.call([program, 'init'])
        opts.dump = True
        self._pull(arg, opts, vc=[program, 'add'])
        subprocess.call([program, 'commit', '-m', '"%s"' % opts.message or 'committed from sqlpython'])        
    
    @options([
              make_option('-f', '--full', action='store_true', help='get dependent objects as well'),
              make_option('-a', '--all', action='store_true', help="all schemas' objects"),
              make_option('-x', '--exact', action='store_true', help="match object name exactly"),
              make_option('-m', '--message', action='store', type='string', dest='message', help="message to save to hg log during commit")])
    def do_hg(self, arg, opts):
        '''hg (opts) (objects):
        Stores DDL on disk and puts files under Mercurial version control.
        Args specify which objects to store, same format as `ls`.'''
        self._vc(arg, opts, 'hg')        

    @options([
              make_option('-f', '--full', action='store_true', help='get dependent objects as well'),
              make_option('-a', '--all', action='store_true', help="all schemas' objects"),
              make_option('-x', '--exact', action='store_true', help="match object name exactly"),
              make_option('-m', '--message', action='store', type='string', dest='message', help="message to save to hg log during commit")])
    def do_bzr(self, arg, opts):
        '''bzr (opts) (objects):
        Stores DDL on disk and puts files under Bazaar version control.
        Args specify which objects to store, same format as `ls`.'''
        self._vc(arg, opts, 'bzr')        

    @options([
              make_option('-f', '--full', action='store_true', help='get dependent objects as well'),
              make_option('-a', '--all', action='store_true', help="all schemas' objects"),
              make_option('-x', '--exact', action='store_true', help="match object name exactly"),
              make_option('-m', '--message', action='store', type='string', dest='message', help="message to save to hg log during commit")])
    def do_git(self, arg, opts):
        '''git (opts) (objects):
        Stores DDL on disk and puts files under git version control.
        Args specify which objects to store, same format as `ls`.'''
        self._vc(arg, opts, 'git')        
        
    all_users_option = make_option('-a', action='store_const', dest="scope",
                                         default={'col':'', 'view':'user', 'schemas':'user', 'firstcol': ''}, 
                                         const={'col':', owner', 'view':'all', 'schemas':'all', 'firstcol': 'owner, '},
                                         help='Describe all objects (not just my own)')                
    @options([all_users_option,
              make_option('-c', '--col', action='store_true', help='find column'),
              make_option('-t', '--table', action='store_true', help='find table')])                    
    def do_find(self, arg, opts):
        """Finds argument in source code or (with -c) in column definitions."""
       
        capArg = arg.upper()
        
        if opts.col:
            sql = "SELECT table_name, column_name %s FROM %s_tab_columns where column_name like '%%%s%%' ORDER BY %s table_name, column_name;" \
                % (opts.scope['col'], opts.scope['view'], capArg, opts.scope['firstcol'])
        elif opts.table:
            sql = "SELECT table_name %s from %s_tables where table_name like '%%%s%%' ORDER BY %s table_name;" \
                % (opts.scope['col'], opts.scope['view'], capArg, opts.scope['firstcol'])
        else:
            sql = "SELECT * from %s_source where UPPER(text) like '%%%s%%';" % (opts.scope['view'], capArg)
        self.do_select(self.parsed(sql, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix))
        
            
    @options([all_users_option,
              make_option('-l', '--long', action='store_true', help='include column #, comments')])
    def do_describe(self, arg, opts):
        "emulates SQL*Plus's DESCRIBE"
        target = arg.upper()
        objnameclause = ''
        if target:
            objnameclause = "AND    object_name LIKE '%%%s%%' " % target
            object_type, owner, object_name = self.resolve(target)
        if (not target) or (not object_type):
            if opts.long:
                query =  """SELECT o.object_name, o.object_type, o.owner, c.comments
                            FROM   all_objects o
                            LEFT OUTER JOIN all_tab_comments c ON (o.owner = c.owner AND o.object_name = c.table_name AND o.object_type = 'TABLE')
                            WHERE  object_type IN ('TABLE','VIEW','INDEX') 
                            %sORDER BY object_name;""" % objnameclause
            else:
                query =  """SELECT object_name, object_type%s 
                            FROM   %s_objects 
                            WHERE  object_type IN ('TABLE','VIEW','INDEX') 
                            %sORDER BY object_name;""" % \
                            (opts.scope['col'], opts.scope['view'], objnameclause)                                                                             
            return self.do_select(self.parsed(query, terminator=arg.parsed.terminator or ';', 
                                  suffix=arg.parsed.suffix))
        self.stdout.write("%s %s.%s\n" % (object_type, owner, object_name))
        try:
            if object_type == 'TABLE':
                descQ = descQueries[object_type][opts.long]
            else:
                descQ = descQueries[object_type][opts.long]                
            for q in descQ:
                self.do_select(self.parsed(q, terminator=arg.parsed.terminator or ';' , suffix=arg.parsed.suffix), 
                               bindVarsIn={'object_name':object_name, 'owner':owner})            
        except KeyError:
            if object_type == 'PACKAGE':
                packageContents = self.select_scalar_list(descQueries['PackageObjects'][0], {'package_name':object_name, 'owner':owner})
                for packageObj_name in packageContents:
                    self.stdout.write('Arguments to %s\n' % (packageObj_name))
                    sql = self.parsed(descQueries['PackageObjArgs'][0], terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix)
                    self.do_select(sql, bindVarsIn={'package_name':object_name, 'owner':owner, 'object_name':packageObj_name})


    def do_deps(self, arg):
        '''Lists all objects that are dependent upon the object.'''
        target = arg.upper()
        object_type, owner, object_name = self.resolve(target)
        if object_type == 'PACKAGE BODY':
            q = "and (type != 'PACKAGE BODY' or name != :object_name)'"
            object_type = 'PACKAGE'
        else:
            q = ""
        q = """SELECT name,
          type
          from user_dependencies
          where
          referenced_name like :object_name
          and	referenced_type like :object_type
          and	referenced_owner like :owner
          %s;""" % (q)
        self.do_select(self.parsed(q, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix), 
                       bindVarsIn={'object_name':object_name, 'object_type':object_type, 'owner':owner})

    def do_comments(self, arg):
        'Prints comments on a table and its columns.'
        target = arg.upper()        
        object_type, owner, object_name, colName = self.resolve_with_column(target)
        if object_type:
            self._execute(queries['tabComments'], {'table_name':object_name, 'owner':owner})
            self.stdout.write("%s %s.%s: %s\n" % (object_type, owner, object_name, self.curs.fetchone()[0]))
            if colName:
                sql = queries['oneColComments']
                bindVarsIn={'owner':owner, 'object_name': object_name, 'column_name': colName}
            else:
                sql = queries['colComments'] 
                bindVarsIn={'owner':owner, 'object_name': object_name}
            self.do_select(self.parsed(sql, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix), 
                           bindVarsIn=bindVarsIn)

    def _resolve(self, identifier):
        parts = identifier.split('.')
        if len(parts) == 2:
            owner, object_name = parts
            object_type = self.select_scalar_list('SELECT object_type FROM all_objects WHERE owner = :owner AND object_name = :object_name',
                              {'owner': owner, 'object_name': object_name.upper()}
                              )[0]
        elif len(parts) == 1:
            object_name = parts[0]
            self._execute(queries['resolve'], {'objName':object_name.upper()})
            object_type, object_name, owner = self.curs.fetchone()
        return object_type, owner, object_name
        
    def resolve(self, identifier):
        """Checks (my objects).name, (my synonyms).name, (public synonyms).name
        to resolve a database object's name. """
        try:
            return self._resolve(identifier)
        except (TypeError, IndexError):
            print 'Could not resolve object %s.' % identifier
            return '', '', ''

    def resolve_with_column(self, identifier):
        colName = None
        object_type, owner, object_name = self.resolve(identifier)
        if not object_type:
            parts = identifier.split('.')
            if len(parts) > 1:
                colName = parts[-1]
                identifier = '.'.join(parts[:-1])
                object_type, owner, object_name = self.resolve(identifier)
        return object_type, owner, object_name, colName
        
    def do_resolve(self, arg):
        target = arg.upper()
        self.stdout.write(','.join(self.resolve(target))+'\n')

    def spoolstop(self):
        if self.spoolFile:
            self.stdout = self.stdoutBeforeSpool
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
            self.stdout = self.spoolFile

    def do_write(self, args):
        'Obsolete command.  Use (query) > outfilename instead.'
        print self.do_write.__doc__
        return

    def do_compare(self, args):
        """COMPARE query1 TO query2 - uses external tool to display differences.

        Sorting is recommended to avoid false hits.
        Will attempt to use a graphical diff/merge tool like kdiff3, meld, or Araxis Merge, 
        if they are installed."""
        #TODO: Update this to use pyparsing
        fnames = []
        args2 = args.split(' to ')
        if len(args2) < 2:
            print self.do_compare.__doc__
            return
        for n in range(len(args2)):
            query = args2[n]
            fnames.append('compare%s.txt' % n)
            #TODO: update this terminator-stripping
            if query.rstrip()[-1] != self.terminator: 
                query = '%s%s' % (query, self.terminator)
            self.onecmd_plus_hooks('%s > %s' % (query, fnames[n]))
        diffMergeSearcher.invoke(fnames[0], fnames[1])

    bufferPosPattern = re.compile('\d+')
    rangeIndicators = ('-',':')

    def do_psql(self, arg):
        '''Shortcut commands emulating psql's backslash commands.

        \c connect
        \d desc
        \e edit
        \g run
        \h help
        \i load
        \o spool
        \p list
        \q quit
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
        try:
            abbrev = words[0]
        except IndexError:
            return
        try:
            args = words[1]
        except IndexError:
            args = ''
        try:
            return self.onecmd('%s %s%s%s' % (commands[abbrev], args, arg.parsed.terminator, arg.parsed.suffix))
        except KeyError:
            print 'psql command \%s not yet supported.' % abbrev

    @options([all_users_option])
    def do__dir_tables(self, arg, opts):
        '''
        Lists all tables whose names match argument.
        '''        
        sql = """SELECT table_name, 'TABLE' as type%s FROM %s_tables WHERE table_name LIKE '%%%s%%';""" % \
                       (opts.scope['col'], opts.scope['view'], arg.upper())
        if self.sql_echo:
            print sql
        self.do_select(self.parsed(sql, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix))
        
    @options([all_users_option])
    def do__dir_views(self, arg, opts):
        '''
        Lists all views whose names match argument.
        '''
        sql = """SELECT view_name, 'VIEW' as type%s FROM %s_views WHERE view_name LIKE '%%%s%%';""" % \
                       (opts.scope['col'], opts.scope['view'], arg.upper())
        if self.sql_echo:
            print sql
        self.do_select(self.parsed(sql, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix))
        
    def do__dir_indexes(self, arg):
        '''
        Called with an exact table name, lists the indexes of that table.
        Otherwise, acts as shortcut for `ls index/*(arg)*`
        '''
        try:
            table_type, table_owner, table_name = self._resolve(arg)
        except TypeError, IndexError:
            return self.onecmd('ls Index/*%s*' % arg)
        sql = """SELECT owner, index_name, index_type FROM all_indexes
                 WHERE  table_owner = :table_owner
                 AND    table_name = :table_name;
                 ORDER BY owner, index_name"""
        self.do_select(self.parsed(sql, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix),
                       bindVarsIn = {'table_owner': table_owner, 'table_name': table_name})

    def do__dir_tablespaces(self, arg):
        '''
        Lists all tablespaces.
        '''
        sql = """SELECT tablespace_name, file_name from dba_data_files;"""
        if self.sql_echo:
            print sql
        self.do_select(self.parsed(sql, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix))

    def do__dir_schemas(self, arg):
        '''
        Lists all object owners, together with the number of objects they own.
        '''
        sql = """SELECT owner, count(*) AS objects FROM all_objects GROUP BY owner ORDER BY owner;"""
        if self.sql_echo:
            print sql
        self.do_select(self.parsed(sql, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix))

    def do_head(self, arg):
        '''Shortcut for SELECT * FROM <arg>;10
        The terminator (\\t, \\g, \\x, etc.) and number of rows can
        be changed as for any other SELECT statement.'''
        sql = self.parsed('SELECT * FROM %s;' % arg, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix)
        sql.parsed['suffix'] = sql.parsed.suffix or '10'
        self.do_select(self.parsed(sql))

    def do_print(self, arg):
        'print VARNAME: Show current value of bind variable VARNAME.'
        if arg:
            if arg[0] == ':':
                arg = arg[1:]
            try:
                self.stdout.write(str(self.binds[arg])+'\n')
            except KeyError:
                self.stdout.write('No bind variable %s\n' % arg)
        else:
            for (var, val) in sorted(self.binds.items()):
                print ':%s = %s' % (var, val)

    def split_on_parser(self, parser, arg):
        try:
            assigner, startat, endat = parser.scanner.scanString(arg).next()
            return (arg[:startat].strip(), arg[endat:].strip())
        except StopIteration:
            return ''.join(arg.split()[:1]), ''
        
    assignmentScanner = Parser(pyparsing.Literal(':=') ^ '=')
    def interpret_variable_assignment(self, arg):
        '''
        Accepts strings like `foo = 'bar'` or `baz := 22`, returning Python
        variables as appropriate
        '''
        var, val = self.split_on_parser(self.assignmentScanner, arg) 
        if not var:
            return None, None
        if (len(val) > 1) and ((val[0] == val[-1] == "'") or (val[0] == val[-1] == '"')):
            return var, val[1:-1]
        try:
            return var, int(val)
        except ValueError:
            try:
                return var, float(val)
            except ValueError:
                # use the conversions implicit in cx_Oracle's select to 
                # cast the value into an appropriate type (dates, for instance)
                try:
                    self.curs.execute('SELECT %s FROM dual' % val)
                    return var, self.curs.fetchone()[0]
                except cx_Oracle.DatabaseError:
                    return var, val  # we give up and assume it's a string
            
    def do_setbind(self, arg):
        '''Sets or shows values of bind (`:`) variables.'''        
        if not arg:
            return self.do_print(arg)
        var, val = self.interpret_variable_assignment(arg)
        if val:
            self.binds[var] = val
        else:
            return self.do_print(var)

    def do_define(self, arg):
        '''Sets or shows values of substitution (`&`) variables.'''
        if not arg:
            for (substvar, val) in sorted(self.substvars.items()):
                print 'DEFINE %s = "%s" (%s)' % (substvar, val, type(val))
        var, val = self.interpret_variable_assignment(arg)
        if val:
            self.substvars[var] = val
        else:
            if var in self.substvars:
                print 'DEFINE %s = "%s" (%s)' % (var, self.substvars[var], type(self.substvars[var]))
    
    def do_exec(self, arg):
        if arg.startswith(':'):
            self.do_setbind(arg[1:])
        else:
            varsUsed = findBinds(arg, self.binds, {})
            try:
                self.curs.execute('begin\n%s;end;' % arg, varsUsed)
            except Exception, e:
                print e

    '''
    Fails:
    select n into :n from test;'''
    
    def anon_plsql(self, line1):
        lines = [line1]
        while True:
            line = self.pseudo_raw_input(self.continuation_prompt)
            if line == 'EOF':
                return
            if line.strip() == '/':
                try:
                    self.curs.execute('\n'.join(lines))
                except Exception, e:
                    print e
                return
            lines.append(line)

    def do_begin(self, arg):
        '''
        PL/SQL blocks can be used normally in sqlpython, though enclosing statements in
        REMARK BEGIN... REMARK END statements can help with parsing speed.'''
        self.anon_plsql('begin ' + arg)

    def do_declare(self, arg):
        self.anon_plsql('declare ' + arg)
        
    def _ls_statement(self, arg, opts):
        if arg:
            target = arg.upper().replace('*','%')
            where = """\nWHERE object_type || '/' || object_name LIKE '%s'
                       OR object_name LIKE '%s'""" % (target, target)
        else:
            where = ''
        if opts.all:
            whose = 'all'
            objname = "owner || '.' || object_name"            
        else:
            whose = 'user'
            objname = 'object_name'            
        if hasattr(opts, 'long') and opts.long:
            moreColumns = ', status, last_ddl_time'
        else:
            moreColumns = ''
            
        # 'Normal' sort order is DATE DESC (maybe), object type ASC, object name ASC
        sortdirection = (hasattr(opts, 'reverse') and opts.reverse and 'DESC') or 'ASC'
        orderby = 'object_type %s, object_name %s' % (sortdirection, sortdirection)
        if hasattr(opts, 'timesort') and opts.timesort:
            orderby = 'last_ddl_time %s, %s' % (('ASC' if hasattr(opts, 'reverse') and opts.reverse else 'DESC'), orderby)
        return {'objname': objname, 'moreColumns': moreColumns,
                'whose': whose, 'where': where, 'orderby': orderby}        
        
    def resolve_many(self, arg, opts):
        opts.long = False
        clauses = self._ls_statement(arg, opts)
        if opts.all:
            clauses['owner'] = 'owner'
        else:
            clauses['owner'] = 'user'
        statement = '''SELECT %(owner)s, object_type, object_name 
                  FROM   %(whose)s_objects %(where)s
                  ORDER BY object_type, object_name''' % clauses
        self._execute(statement)
        return self.curs.fetchall()
    
    @options([make_option('-l', '--long', action='store_true', help='long descriptions'),
              make_option('-a', '--all', action='store_true', help="all schemas' objects"),
              make_option('-t', '--timesort', action='store_true', help="Sort by last_ddl_time"),              
              make_option('-r', '--reverse', action='store_true', help="Reverse order while sorting")])        
    def do_ls(self, arg, opts):
        '''
        Lists objects as through they were in an {object_type}/{object_name} UNIX
        directory structure.  `*` and `%` may be used as wildcards.
        '''
        statement = '''SELECT object_type || '/' || %(objname)s AS name %(moreColumns)s 
                  FROM   %(whose)s_objects %(where)s
                  ORDER BY %(orderby)s;''' % self._ls_statement(arg, opts)
        self.do_select(self.parsed(statement, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix))
        
    @options([make_option('-i', '--ignore-case', dest='ignorecase', action='store_true', help='Case-insensitive search')])        
    def do_grep(self, arg, opts):
        """grep {target} {table} [{table2,...}] - search for {target} in any of {table}'s fields"""    

        targetnames = arg.split()
        pattern = targetnames.pop(0)
        targets = [] 
        for target in targetnames:
            if '*' in target:
                self._execute("SELECT owner, table_name FROM all_tables WHERE table_name LIKE '%s'%s" %
                                  (target.upper().replace('*','%')), arg.terminator)
                for row in self.curs:
                    targets.append('%s.%s' % row)
            else:
                targets.append(target)
        for target in targets:
            print target
            target = target.rstrip(';')
            try:
                self._execute('select * from %s where 1=0' % target) # just to fill description
                if opts.ignorecase:
                    sql = ' or '.join("LOWER(%s) LIKE '%%%s%%'" % (d[0], pattern.lower()) for d in self.curs.description)                                        
                else:
                    sql = ' or '.join("%s LIKE '%%%s%%'" % (d[0], pattern) for d in self.curs.description)
                sql = self.parsed('SELECT * FROM %s WHERE %s;' % (target, sql), terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix)
                self.do_select(sql)
            except Exception, e:
                print e
                import traceback
                traceback.print_exc(file=sys.stdout)                

    def _execute(self, sql, bindvars={}):
        if self.sql_echo:
            print sql
        self.curs.execute(sql, bindvars)

    #@options([make_option('-l', '--long', action='store_true', 
    #                      help='Wordy, easy-to-understand form'),])                
    def do_refs(self, arg):
        '''Lists referential integrity (foreign key constraints) on an object or referring to it.'''
        
        if not arg.strip():
            print 'Usage: refs (table name)'
        result = []
        (type, owner, table_name) = self.resolve(arg.upper())        
        sql = """SELECT constraint_name, r_owner, r_constraint_name 
                             FROM   all_constraints 
                             WHERE  constraint_type = 'R'
                             AND    owner = :owner
                             AND    table_name = :table_name"""
        self._execute(sql, {"owner": owner, "table_name": table_name})
        for (constraint_name, remote_owner, remote_constraint_name) in self.curs.fetchall():
            result.append('%s on %s.%s:' % (constraint_name, owner, table_name))
            
            self._execute("SELECT column_name FROM all_cons_columns WHERE owner = :owner AND constraint_name = :constraint_name ORDER BY position",
                          {'constraint_name': constraint_name, 'owner': owner})
            result.append("    (%s)" % (",".join(col[0] for col in self.curs.fetchall())))
            self._execute("SELECT table_name FROM all_constraints WHERE owner = :remote_owner AND constraint_name = :remote_constraint_name",
                          {'remote_owner': remote_owner, 'remote_constraint_name': remote_constraint_name})
            remote_table_name = self.curs.fetchone()[0]
            result.append("must be in %s:" % (remote_table_name))
            self._execute("SELECT column_name FROM all_cons_columns WHERE owner = :remote_owner AND constraint_name = :remote_constraint_name ORDER BY position",
                              {'remote_constraint_name': remote_constraint_name, 'remote_owner': remote_owner})
            result.append('    (%s)\n' % (",".join(col[0] for col in self.curs.fetchall())))
        remote_table_name = table_name
        remote_owner = owner
        self._execute("""SELECT  owner, constraint_name, table_name, r_constraint_name
                             FROM    all_constraints
                             WHERE   (r_owner, r_constraint_name) IN
                               ( SELECT owner, constraint_name
                                 FROM   all_constraints
                                 WHERE  table_name = :remote_table_name
                                 AND    owner = :remote_owner )""",
                          {'remote_table_name': remote_table_name, 'remote_owner': remote_owner})
        for (owner, constraint_name, table_name, remote_constraint_name) in self.curs.fetchall():
            result.append('%s on %s.%s:' % (constraint_name, owner, table_name))
            self._execute("SELECT column_name FROM all_cons_columns WHERE owner = :owner AND constraint_name = :constraint_name ORDER BY position",
                              {'constraint_name': constraint_name, 'owner': owner})
            result.append("    (%s)" % (",".join(col[0] for col in self.curs.fetchall())))
            self._execute("SELECT table_name FROM all_constraints WHERE owner = :remote_owner AND constraint_name = :remote_constraint_name",
                              {'remote_owner': remote_owner, 'remote_constraint_name': remote_constraint_name})
            remote_table_name = self.curs.fetchone()[0]
            result.append("must be in %s:" % (remote_table_name))
            self._execute("SELECT column_name FROM all_cons_columns WHERE owner = :remote_owner AND constraint_name = :remote_constraint_name ORDER BY position",
                              {'remote_constraint_name': remote_constraint_name, 'remote_owner': remote_owner})
            result.append('    (%s)\n' % (",".join(col[0] for col in self.curs.fetchall())))
        self.stdout.write('\n'.join(result) + "\n")
    
def _test():
    import doctest
    doctest.testmod()
    
if __name__ == "__main__":
    "Silent return implies that all unit tests succeeded.  Use -v to see details."
    _test()
if __name__ == "__main__":
    "Silent return implies that all unit tests succeeded.  Use -v to see details."
    _test()
