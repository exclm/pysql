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
import sys, os, re, sqlpython, cx_Oracle, pyparsing, re, completion
import datetime, pickle, binascii, subprocess, time, itertools, hashlib
import traceback, operator
from cmd2 import Cmd, make_option, options, Statekeeper, Cmd2TestCase
from output_templates import output_templates
from schemagroup import MetaData
from metadata import metaqueries
from plothandler import Plot
from sqlpython import Parser
import imagedetect
import warnings
warnings.filterwarnings('ignore', 'BaseException.message', DeprecationWarning)
try:
    import pylab
except (RuntimeError, ImportError):
    pass

queries = {
'resolve': """
SELECT object_type, object_name, owner FROM (
SELECT object_type, object_name, user AS owner, 1 priority
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
SELECT atc.column_name,
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
            if attr in ('colnames', 'statement', 'bindvars', 'resultset'):
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
    

def offset_to_line(instring, offset):
    r"""
    >>> offset_to_line('abcdefghijkl', 5)
    (0, 'abcdefghijkl', 5)
    >>> offset_to_line('ab\ncd\nefg', 6)
    (2, 'efg', 0)
    >>> offset_to_line('ab\ncd\nefg', 5)
    (1, 'cd\n', 2)
    >>> offset_to_line('abcdefghi\njkl', 5)
    (0, 'abcdefghi\n', 5)
    >>> offset_to_line('abcdefghi\njkl', 700)
    
    """
    lineNum = 0
    for line in instring.splitlines(True):
        if offset < len(line):
            return lineNum, line, offset
        lineNum += 1
        offset -= len(line)

class BlobDisplayer(object):
    folder_name = 'sqlpython_blob_store'
    imgwidth = 400
    def folder_ok(self):
        if not os.access(self.folder_name, os.F_OK):
            try:
                os.mkdir(self.folder_name)
                readme = open(os.path.join(self.folder_name, 'README.txt'),'w')
                readme.write('''
                                Temporary files for display of BLOBs from within
                                sqlpython.  Delete when sqlpython is closed.''')
                readme.close()
            except:
                return False
        return True
    def __init__(self, blob, under_limit):
        self.url = ''
        if under_limit:
            self.blob = blob.read()
            self.hashed = hashlib.md5(self.blob).hexdigest()
            self.extension = imagedetect.extension_from_data(self.blob)
            if self.folder_ok():
                self.file_name = '%s/%s%s' % (
                    os.path.join(os.getcwd(), self.folder_name), 
                    self.hashed, self.extension)
                self.url = 'file://%s' % self.file_name
                if not os.access(self.file_name, os.F_OK):
                    outfile = open(self.file_name, 'wb')
                    outfile.write(self.blob)
                    outfile.close()
    def __str__(self):
        if self.url:
            return '(BLOB at %s)' % self.url
        else:
            return '(BLOB)'
    def html(self):
        if self.url:
            return '<a href="%s"><img src="%s" width="%d" /></a>' % (
                self.url, self.url, self.imgwidth)
        else:
            return '(BLOB not saved, check bloblimit)'
        
class Abbreviatable_List(list):
    def match(self, target):
        target = target.lower()
        result = [i for i in self if i.startswith(target)]
        if len(result) == 0:
            raise ValueError, 'None of %s start with %s' % (str(self), target)
        elif len(result) > 1:
            raise ValueError, 'Too many matches: %s' % str(result)
        return result[0]
    
class sqlpyPlus(sqlpython.sqlpython):
    defaultExtension = 'sql'
    abbrev = True    
    sqlpython.sqlpython.shortcuts.update({':': 'setbind', 
                                          '\\': 'psql', 
                                          '@': 'get'})
    multilineCommands = '''select insert update delete tselect
                      create drop alter _multiline_comment'''.split()
    sqlpython.sqlpython.noSpecialParse.append('spool')
    commentGrammars = pyparsing.Or([pyparsing.cStyleComment, pyparsing.Literal('--') + pyparsing.restOfLine])
    prefixParser = pyparsing.Optional(pyparsing.Word(pyparsing.nums)('connection_number') 
                                      + ':')
    reserved_words = [
            'alter', 'begin', 'comment', 'create', 'delete', 'drop', 'end', 'for', 'grant', 
            'insert', 'intersect', 'lock', 'minus', 'on', 'order', 'rename', 
            'resource', 'revoke', 'select', 'share', 'start', 'union', 'update', 
            'where', 'with']    
    default_file_name = 'afiedt.buf'
    def __init__(self):
        sqlpython.sqlpython.__init__(self)
        self.binds = CaselessDict()
        self.settable += '''autobind bloblimit colors commit_on_exit 
                            default_rdbms maxfetch maxtselctrows 
                            rows_remembered scan serveroutput 
                            sql_echo timeout heading wildsql version'''.split()
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
        self.substvars = {}
        self.result_history = []
        self.rows_remembered = 10000
        self.bloblimit = 5
        self.default_rdbms = 'oracle'
        self.rdbms_supported = Abbreviatable_List('oracle postgres mysql'.split())
        self.version = 'SQLPython %s' % sqlpython.__version__
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
            self.perror('Not connected.')
            return '', '', ''
        return cmd, arg, line

    def perror(self, err, statement=None):
        if self.debug:
            traceback.print_exc()            
        try:
            linenum, line, offset = offset_to_line(statement.parsed.raw, err.message.offset)
            print line.strip()
            print '%s*' % (' ' * offset)
            print 'ERROR at line %d:' % (linenum + 1)
        except AttributeError:
            pass        
        print str(err)
    def dbms_output(self):
        "Dumps contents of Oracle's DBMS_OUTPUT buffer (where PUT_LINE goes)"
        try:
            line = self.curs.var(cx_Oracle.STRING)
            status = self.curs.var(cx_Oracle.NUMBER)
            self.curs.callproc('dbms_output.get_line', [line, status])
            while not status.getvalue():
                self.poutput(line.getvalue())
                self.poutput('\n')
                self.curs.callproc('dbms_output.get_line', [line, status])
        except AttributeError:
            pass
        
    def postcmd(self, stop, line):
        """Hook method executed just after a command dispatch is finished."""        
        if (    hasattr(self, 'rdbms') 
            and (self.rdbms == 'oracle') 
            and self.serveroutput):
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
        if (self.rdbms == 'oracle'):
            if new:
                self.curs.callproc('dbms_output.enable', [])        
            else:
                self.curs.callproc('dbms_output.disable', [])        
        
    def do_shortcuts(self,arg):
        """Lists available first-character shortcuts
        (i.e. '!dir' is equivalent to 'shell dir')"""
        for (scchar, scto) in self.shortcuts:
            self.poutput('%s: %s' % (scchar, scto))

    tableNameFinder = re.compile(r'from\s+([\w$#_"]+)', re.IGNORECASE | re.MULTILINE | re.DOTALL)          
    def formattedForSql(self, datum):
        if datum is None:
            return 'NULL'
        elif isinstance(datum, basestring):
            return "'%s'" % datum.replace("'","''")
        try:
            return datum.strftime("TO_DATE('%Y-%m-%d %H:%M:%S', 'YYYY-MM-DD HH24:MI:SS')")
        except AttributeError:
            return str(datum)
              
    def tabular_output(self, outformat, tblname=None):
        if tblname:
            self.tblname = tblname
        else:
            try:
                self.tblname = self.tableNameFinder.search(self.querytext).group(1)
            except AttributeError:
                self.tblname = ''
        if outformat in output_templates:
            self.colnamelen = max(len(colname) for colname in self.colnames)
            result = output_templates[outformat].generate(formattedForSql=self.formattedForSql, **self.__dict__)        
        elif outformat == '\\t': # transposed
            rows = [self.colnames]
            rows.extend(list(self.rows))
            transpr = [[rows[y][x] for y in range(len(rows))]for x in range(len(rows[0]))] # matrix transpose
            newdesc = [['ROW N.'+str(y),10] for y in range(len(rows))]
            for x in range(len(self.coltypes)):
                if str(self.coltypes[x]) == "<type 'cx_Oracle.BINARY'>":  # handles RAW columns
                    rname = transpr[x][0]
                    transpr[x] = map(binascii.b2a_hex, transpr[x])
                    transpr[x][0] = rname
            self.colnames = ['ROW N.%d' % y for y in range(len(rows))]                    
            self.colnames[0] = 'COLUMN NAME'
            self.coltypes = [str] * len(self.colnames)
            result = '\n' + self.pmatrix(transpr)            
        elif outformat in ('\\l', '\\L', '\\p', '\\b'):
            plot = Plot()
            plot.build(self, outformat)
            plot.shelve()                
            plot.draw()
            return ''
        else:
            result = self.pmatrix(self.rows, 
                                  self.maxfetch, heading=self.heading, 
                                  restructuredtext = (outformat == '\\r'))
        return result
        
    legalOracle = re.compile('[a-zA-Z_$#]')

    def select_scalar_list(self, sql, binds={}):
        self._execute(sql, binds)
        return [r[0] for r in self.curs.fetchall()]
    
    columnNameRegex = re.compile(
        r'select\s+(.*)from',
        re.IGNORECASE | re.DOTALL | re.MULTILINE)        
    def completedefault(self, text, line, begidx, endidx):
        (username, schemas) = self.metadata()
        segment = completion.whichSegment(line)
        text = text.upper()
        if segment in ('select', 'where', 'having', 'set', 'order by', 'group by'):
            completions = [c for c in schemas[username].column_names if c.startswith(text)] \
                          or [c for c in schemas.qual_column_names if c.startswith(text)]
                          # TODO: the latter not working
        elif segment in ('from', 'update', 'insert into'):
            completions = [t for t in schemas[username].table_names if t.startswith(text)]
        elif segment == 'beginning':
            completions = [n for n in self.get_names() if n.startswith('do_')] + [
                           'insert', 'update', 'delete', 'drop', 'alter', 'begin', 'declare', 'create']
            completions = [c for c in completions if c.startswith(text)]     
        elif segment:
            completions = [t for t in schemas[username].table_names if t.startswith(text)]
        else:
            completions = [r for r in completion.reserved if r.startswith(text)]
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
                self.pfeedback('No columns found matching criteria.')
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
            self.pfeedback('No columns found matching criteria.')
            return 'null from dual'        
        return result + ' ' + columnlist.remainder

    do_prompt = Cmd.poutput
        
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
            self.pfeedback('Substitution variable %s found in:' % fullexpr)
            self.pfeedback(raw[max(subst.start()-20, 0):subst.end()+20])
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
            self.pfeedback('Substituted %s for %s' % (val, fullexpr))
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
    terminators = '; \\C \\t \\i \\p \\l \\L \\b \\r'.split() + output_templates.keys()

    @options([make_option('-r', '--row', type="int", default=-1,
                          help='Bind row #ROW instead of final row (zero-based)')])    
    def do_bind(self, arg, opts):
        '''
        Inserts the results from the final row in the last completed SELECT statement
        into bind variables with names corresponding to the column names.  When the optional 
        `autobind` setting is on, this will be issued automatically after every query that 
        returns exactly one row.
        '''
        try:
            self.pystate['r'][-1][opts.row].bind()
        except IndexError:
            self.poutput(self.do_bind.__doc__)
        
    def age_out_resultsets(self):
        total_len = sum(len(rs) for rs in self.pystate['r'])
        for (i, rset) in enumerate(self.pystate['r'][:-1]):
            if total_len <= self.rows_remembered:
                return
            total_len -= len(rset)
            self.pystate['r'][i] = []
        
    def rowlimit(self, arg):
        try:
            rowlimit = int(arg.parsed.suffix)
        except (TypeError, ValueError):
            rowlimit = None
        if arg.parsed.terminator == '\\t':
            rowlimit = rowlimit or self.maxtselctrows
        return rowlimit
        
    def do_select(self, arg, bindVarsIn=None, terminator=None):
        """Fetch rows from a table.

        Limit the number of rows retrieved by appending
        an integer after the terminator
        (example: SELECT * FROM mytable;10 )

        Output may be formatted by choosing an alternative terminator
        ("help terminators" for details)
        """
        bindVarsIn = bindVarsIn or {}
        rowlimit = self.rowlimit(arg)
        self.varsUsed = self.findBinds(arg, bindVarsIn)
        if self.wildsql:
            selecttext = self.expandWildSql(arg)
        else:
            selecttext = arg
        self.querytext = 'select ' + selecttext
        if self.varsUsed:
            self.curs.execute(self.querytext, self.varsUsed)
        else: # this is an ugly workaround for the evil paramstyle curse upon DB-API2
            self.curs.execute(self.querytext)
        self.rows = self.curs.fetchmany(min(self.maxfetch, (rowlimit or self.maxfetch)))
        self.colnames = [d[0] for d in self.curs.description]
        self.coltypes = [d[1] for d in self.curs.description]
        if cx_Oracle.BLOB in self.coltypes:
            self.rows = [
                 [(    (coltype == cx_Oracle.BLOB) 
                   and BlobDisplayer(datum, (rownum < self.bloblimit)))
                   or datum
                   for (datum, coltype) in zip(row, self.coltypes)]
                 for (rownum, row) in enumerate(self.rows)]
        self.rc = len(self.rows)
        if self.rc != 0:
            resultset = ResultSet()
            resultset.colnames = [d[0].lower() for d in self.curs.description]
            resultset.pystate = self.pystate
            resultset.statement = 'select ' + selecttext
            resultset.varsUsed = self.varsUsed
            resultset.extend([Result(r) for r in self.rows])
            for row in resultset:
                row.resultset = resultset
            self.pystate['r'].append(resultset)
            self.age_out_resultsets()            
            self.poutput('\n%s\n' % (self.tabular_output(arg.parsed.terminator)))
        if self.rc == 0:
            self.pfeedback('\nNo rows Selected.\n')
        elif self.rc == 1: 
            self.pfeedback('\n1 row selected.\n')
            if self.autobind:
                self.do_bind('')
        elif (self.rc < self.maxfetch and self.rc > 0):
            self.pfeedback('\n%d rows selected.\n' % self.rc)
        else:
            self.pfeedback('\nSelected Max Num rows (%d)' % self.rc)
        
    def do_cat(self, arg):
        '''Shortcut for SELECT * FROM
        return self.do_select(self.parsed('SELECT * FROM %s;' % arg, 
                                          terminator = arg.parsed.terminator or ';', 
                                          suffix = arg.parsed.suffix))'''
        return self.onecmd('SELECT * FROM %s%s%s' % (arg, arg.parsed.terminator or ';',
                                                     arg.parsed.suffix or ''))

    @options([make_option('-d', '--dump', action='store_true', help='dump results to files'),
              make_option('-f', '--full', action='store_true', help='get dependent objects as well'),
              make_option('-l', '--lines', action='store_true', help='print line numbers'),
              make_option('-n', '--num', type='int', help='only code near line #num'),
              make_option('-w', '--width', type='int', default=5, 
                          help='# of lines before and after --lineNo'),
              make_option('-a', '--all', action='store_true', help="all schemas' objects"),
              #make_option('-x', '--exact', action='store_true', help="match object name exactly")
              ])               
    def do_pull(self, arg, opts):        
        """Displays source code."""
        self._pull(arg, opts)

    def _pull(self, arg, opts, vc=None):        
        opts.exact = True
        statekeeper = Statekeeper(opts.dump and self, ('stdout',))
        (username, schemas) = self.metadata()
        try:
            for metadata in self._matching_database_objects(arg, opts):
                self.poutput(metadata.descriptor(qualified=True))
                txt = metadata.db_object.get_ddl()
                if opts.get('lines'):
                    txt = self._with_line_numbers(txt)
    
                if opts.dump:
                    path = os.path.join(metadata.schema_name.lower(), metadata.db_type.lower()) \
                           .replace(' ', '_')
                    try:
                        os.makedirs(path)
                    except OSError:
                        pass
                    filename = os.path.join(path, '%s.sql' % metadata.object_name.lower())
                    self.stdout = open(filename, 'w')
                if opts.get('num') is not None:
                    txt = txt.splitlines()
                    txt = centeredSlice(txt, center=opts.num+1, width=opts.width)
                    txt = '\n'.join(txt)
                else:
                    txt = 'REMARK BEGIN %s\n%s\nREMARK END\n' % (metadata.descriptor(qualified=True), txt)

                self.poutput(txt)
                if opts.full:
                    # Hmm... dependent objects...
            
                    if opts.full:
                        for dependent_type in ('OBJECT_GRANT', 'CONSTRAINT', 'TRIGGER'):        
                            try:
                                self.poutput('REMARK BEGIN\n%s\nREMARK END\n\n' % str(self.curs.callfunc('DBMS_METADATA.GET_DEPENDENT_DDL', cx_Oracle.CLOB,
                                                                         [dependent_type, object_name, owner])))
                            except cx_Oracle.DatabaseError:
                                pass
                if opts.dump:
                    self.stdout.close()
                    if vc:
                        subprocess.call(vc + [filename])                    
        except:
            statekeeper.restore()
            raise
        statekeeper.restore()   
          
    def _with_line_numbers(self, txt):
        txt = txt.splitlines()
        template = "%%-%dd:%%s" % len(str(len(txt)))
        txt = '\n'.join(template % (n+1, line) for (n, line) in 
                        enumerate(txt))
        return txt
                        
    def _show_shortcut(self, shortcut, argpieces):
        try:
            newarg = argpieces[1]
            if newarg == 'on':
                try:
                    newarg = argpieces[2]
                except IndexError:
                    pass
        except IndexError:
            newarg = ''
        return self.onecmd(shortcut + ' ' + newarg)
    
    def do_show(self, arg):
        '''
        show                  - display value of all sqlpython parameters
        show (parameter name) - display value of a sqlpython parameter
        show parameter (parameter name) - display value of an ORACLE parameter
        show err (object type/name)     - errors from latest PL/SQL object compilation.
        show all err (type/name)        - all compilation errors from the user's PL/SQL objects.
        show (index/schema/tablespace/trigger/view/constraint/comment) on (table)
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
            argpieces = [a for a in argpieces if not a.startswith('-')]
            try:
                for (kwd, shortcut) in (
                        ('ind', '\\di'), ('schema', '\\dn'), 
                        ('tablesp', '\\db'), ('trig', '\\dg'), 
                        ('view', '\\dv'), ('cons', '\\dc'),
                        ('comm', '\\dd'), ('ref', 'ref')):
                    if argpieces[0].lower().startswith(kwd):
                        return self._show_shortcut(shortcut, argpieces)
                if argpieces[0][:3] == 'err':
                    return self._show_errors(all_users=False, limit=1, targets=argpieces[1:])
                elif (argpieces[0], argpieces[1][:3]) == ('all','err'):
                    return self._show_errors(all_users=False, limit=None, targets=argpieces[2:])
            except IndexError:
                pass
            return Cmd.do_show(self, arg)
            
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
             ])                    
    def do_find(self, arg, opts):
        """Finds argument in source code or (with -c) in column definitions."""
              
        seek = self._regex(arg, exact=opts.col)
        qualified = opts.get('all')
        for m in self._matching_database_objects('*', opts):
            if opts.col:
                if hasattr(m.db_object, 'columns'):
                    for col in m.db_object.columns:
                        if isinstance(col, tuple):
                            col = col[1]  # will become unnecessary once gerald views return dicts of columns
                        if seek.search(col):
                            self.poutput('%s.%s' % (m.descriptor(qualified), col))
            else:
                if hasattr(m.db_object, 'source'):
                    name_printed = False
                    for (line_num, line) in m.db_object.source:
                        if seek.search(line):
                            if not name_printed:
                                self.poutput(m.descriptor(qualified))
                                name_printed = True
                            self.poutput('%d: %s' % (line_num, line))
            
    def _col_type_descriptor(self, col):
        if 'precision' in col:
            return '%s(%d,%d)' % (col['type'], col['length'], col['precision'])
        elif 'length' in col:
            return '%s(%d)' % (col['type'], col['length'])
        else:
            return col['type']
        
    def _key_columns(self, tbl, type):
        columns = [c['columns'] for c in tbl.constraints.values() if c['type'] == type]
        if columns:
            return reduce(list.extend, columns)
        else:
            return []
        
    @options([all_users_option,
              make_option('-l', '--long', action='store_true', help='include column #, comments'),
              make_option('-A', '--alpha', action='store_true', help='List columns alphabetically')])
    def do_describe(self, arg, opts):
        opts.exact = True
        rowlimit = self.rowlimit(arg)
        if opts.alpha:
            sortkey = operator.itemgetter('name')
        else:
            sortkey = operator.itemgetter('sequence')
        for m in self._matching_database_objects(arg, opts):
            self.tblname = m.descriptor(qualified=opts.get('all'))
            self.pfeedback(self.tblname)
            if opts.long and hasattr(m.db_object, 'comments'):
                if m.db_object.comments:
                    self.poutput(m.db_object.comments) 
            if hasattr(m.db_object, 'columns') and not isinstance(m.db_object.columns, list): # drop once gerald returns column dicts for views
                cols = sorted(m.db_object.columns.values(), key=sortkey)[:rowlimit]
                if opts.long:
                    primary_key_columns = self._key_columns(m.db_object, 'Primary')
                    unique_key_columns = self._key_columns(m.db_object, 'Unique')
                    self.colnames = 'N Name Nullable Type Key Default Comments'.split()
                    self.rows = [(col['sequence'], col['name'], (col['nullable'] and 'NULL') or 'NOT NULL',
                                  self._col_type_descriptor(col), 
                                  ((col['name'] in primary_key_columns) and 'P') or
                                  ((col['name'] in unique_key_columns) and 'U') or '',
                                  col.get('default') or '', col.get('comment') or '')
                                 for col in cols]
                else:
                    self.colnames = 'Name Nullable Type'.split()
                    self.rows = [(col['name'], (col['nullable'] and 'NULL') or 'NOT NULL', self._col_type_descriptor(col)) 
                                 for col in cols]
                self.coltypes = [str] * len(self.colnames)
                self.poutput(self.tabular_output(arg.parsed.terminator, self.tblname) + '\n\n')
            elif hasattr(m.db_object, 'increment_by'):
                self.colnames = 'name min_value max_value increment_by'.split()
                self.coltypes = [str, int, int, int]
                self.rows = [(getattr(m.db_object, p) for p in self.colnames)]
                self.poutput(self.tabular_output(arg.parsed.terminator, self.tblname) + '\n\n')
            elif hasattr(m.db_object, 'source'):
                end_heading = re.compile(r'\bDECLARE|BEGIN\b', re.IGNORECASE)
                for (index, (ln, line)) in enumerate(m.db_object.source):
                    if end_heading.search(line):
                        break
                self.poutput(''.join(l for (ln, l) in m.db_object.source[:index]))
                        
            
    def do_deps(self, arg):
        '''Lists all objects that are dependent upon the object.'''
        #TODO: Can this be Geraldized?
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

    @options([all_users_option])        
    def do_comments(self, arg, opts):
        'Prints comments on a table and its columns.'
        qualified = opts.get('all')
        for m in self._matching_database_objects(arg, opts):
            if hasattr(m.db_object, 'comments'):
                self.poutput(m.descriptor(qualified))
                self.poutput(m.db_object.comments)
                if hasattr(m.db_object, 'columns'):
                    columns = m.db_object.columns.values()
                    columns.sort(key=operator.itemgetter('sequence'))
                    for col in columns:
                        comment = col.get('comment')
                        if comment:
                            self.poutput('%s: %s' % (col['name'], comment))
                        else:
                            self.poutput(col['name'])

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
            self.pfeedback('Could not resolve object %s.' % identifier)
            return '', '', ''
        
    def spoolstop(self):
        if self.spoolFile:
            self.stdout = self.stdoutBeforeSpool
            self.pfeedback('Finished spooling to ', self.spoolFile.name)
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
            self.pfeedback('Sending output to %s (until SPOOL OFF received)' % (arg))
            self.spoolFile = open(arg, 'w')
            self.stdout = self.spoolFile

    def sqlfeedback(self, arg):
        if self.sql_echo:
            self.pfeedback(arg)
            
    def do_write(self, args):
        'Obsolete command.  Use (query) > outfilename instead.'
        self.poutput(self.do_write.__doc__)
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
            self.pfeedback(self.do_compare.__doc__)
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
        \dc _dir_constraints
        \dd comments
        \dg _dir_triggers
        \dn _dir_schemas
        \dt _dir_tables
        \dv _dir_views
        \di _dir_indexes
        \? help psql'''
        commands = {}
        for c in self.do_psql.__doc__.splitlines()[2:]:
            (abbrev, command) = c.split(None, 1)
            commands[abbrev] = command
        parts = arg.parsed.raw.split(None,1)
        abbrev = parts[0]
        try:
            remainder = parts[1]
        except IndexError:
            remainder = ''
        if abbrev in commands:
            newcommand = '%s %s' % (commands[abbrev], remainder)
            return self.onecmd(newcommand)
        else:
            self.perror('No abbreviated command for %s' % abbrev)
            self.perror(self.do_psql.__doc__)
            
    def _do_dir(self, type, arg, opts):
        self.do_ls("%s/%s%s%s" % (type, str(arg), arg.parsed.terminator, arg.parsed.suffix), opts)

    standard_options = [
              make_option('-l', '--long', action='store_true', help='long descriptions'),
              make_option('-a', '--all', action='store_true', help="all schemas' objects"),
              make_option('-i', '--immediate', action='store_true', help="force immediate refresh of metadata"),
              #make_option('-t', '--timesort', action='store_true', help="Sort by last_ddl_time"),              
              make_option('-r', '--reverse', action='store_true', help="Reverse order while sorting")]
    
    @options(standard_options)
    def do__dir_tables(self, arg, opts):
        'Shortcut for ``ls table/``'
        self._do_dir('table', arg, opts)

    @options(standard_options)
    def do__dir_views(self, arg, opts):
        'Shortcut for ``ls table/``'
        self._do_dir('view', arg, opts)

    @options(standard_options)
    def do__dir_(self, arg, opts):
        'Shortcut for ``ls table/``'
        self._do_dir('', arg, opts)

    @options(standard_options)
    def do__dir_(self, arg, opts):
        'Shortcut for ``ls table/``'
        self._do_dir('', arg, opts)
        
    def _str_index(self, idx, long=False):
        return '%s (%s) %s %s' % (idx['name'], ','.join(idx['columns']),
                                  idx['type'], (idx['unique'] and 'unique') or '')

    def _str_constraint(self, cons, long=False):
        if 'condition' in cons:
            details = '(%s)' % cons['condition']
        elif 'reftable' in cons:
            details = '(%s) in %s' % (','.join(cons['columns']), cons['reftable'])
        elif 'columns' in cons:
            details = '(%s)' % ','.join(cons['columns'])
        else:
            details = ''
        return '%7s %s: %s %s' % (cons['type'], cons['name'], details,
                                  ((not cons['enabled']) and 'DISABLED') or '')


    def _str_trigger(self, trig, long=False):
        result = 'Trigger %s %s %s for each %s' % (trig.name, trig.scope, ','.join(trig.events), trig.level)
        if long:
            result = '%s\n\n%s\n\n' % (result, trig.sql)
        return result
        
    def do__dir_(self, arg, opts, plural_name, str_function):
        long = opts.get('long')
        reverse = opts.get('reverse') or False
        for obj in self._matching_database_objects(arg, opts):
            if hasattr(obj.db_object, plural_name):
                self.pfeedback('%s on %s' % (plural_name.title(), obj.descriptor(opts.get('all'))))
                result = [str_function(depobj, long) for depobj in getattr(obj.db_object, plural_name).values()]
                result.sort(reverse=opts.get('reverse') or False)
                self.poutput('\n'.join(result))
        
    @options(standard_options)
    def do__dir_indexes(self, arg, opts):
        '''
        Called with an exact table name, lists the indexes of that table.
        Otherwise, acts as shortcut for `ls index/*(arg)*`
        '''
        self.do__dir_(arg, opts, 'indexes', self._str_index)

    @options(standard_options)
    def do__dir_constraints(self, arg, opts):
        '''
        Called with an exact table name, lists the indexes of that table.
        Otherwise, acts as shortcut for `ls index/*(arg)*`
        '''
        self.do__dir_(arg, opts, 'constraints', self._str_constraint)

    @options(standard_options)
    def do__dir_triggers(self, arg, opts):
        '''
        Called with an exact table name, lists the indexes of that table.
        Otherwise, acts as shortcut for `ls index/*(arg)*`
        '''
        self.do__dir_(arg, opts, 'triggers', self._str_trigger)
        
    def do__dir_tablespaces(self, arg):
        '''
        Lists all tablespaces.
        '''
        sql = """SELECT tablespace_name, file_name from dba_data_files;"""
        self.sqlfeedback(sql)
        self.do_select(self.parsed(sql, terminator=arg.parsed.terminator or ';', suffix=arg.parsed.suffix))

    def do__dir_schemas(self, arg):
        '''
        Lists all object owners, together with the number of objects they own.
        '''
        sql = """SELECT owner, count(*) AS objects FROM all_objects GROUP BY owner ORDER BY owner;"""
        self.sqlfeedback(sql)
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
                self.poutput(str(self.binds[arg])+'\n')
            except KeyError:
                self.poutput('No bind variable %s\n' % arg)
        else:
            for (var, val) in sorted(self.binds.items()):
                self.poutput(':%s = %s' % (var, val))

    def split_on_parser(self, parser, arg):
        try:
            assigner, startat, endat = parser.scanner.scanString(arg).next()
            return (arg[:startat].strip(), arg[endat:].strip())
        except StopIteration:
            return ''.join(arg.split()[:1]), ''
        
    assignmentSplitter = re.compile(':?=')
    def interpret_variable_assignment(self, arg):
        '''
        Accepts strings like `foo = 'bar'` or `baz := 22`, 
        returns (assigned? (T/F), variable, new-value)

        >>> s = sqlpyPlus()
        >>> s.interpret_variable_assignment(s.parsed("foo = 'bar'"))
        (True, 'foo', 'bar')
        >>> s.interpret_variable_assignment(s.parsed("baz := 22"))
        (True, 'baz', 22)
        >>> s.interpret_variable_assignment(s.parsed("foo"))
        (False, 'foo', None)    
        '''
        arg = self.parsed(arg)
        try:
            var, val = self.assignmentSplitter.split(arg.parsed.expanded, maxsplit=1)
        except ValueError:
            return False, arg.parsed.expanded.split()[-1] or None, None 
        var = var.split()[-1]
        val = val.strip()
        if (len(val) > 1) and ((val[0] == val[-1] == "'") or (val[0] == val[-1] == '"')):
            return True, var, val[1:-1]
        try:
            return True, var, int(val)
        except ValueError:
            try:
                return True, var, float(val)
            except ValueError:
                # use the conversions implicit in cx_Oracle's select to 
                # cast the value into an appropriate type (dates, for instance)
                try:
                    if self.rdbms == 'oracle':
                        sql = 'SELECT %s FROM dual'
                    else:
                        sql = 'SELECT %s'
                    self.curs.execute(sql % val)
                    return True, var, self.curs.fetchone()[0]
                except:   # should not be bare - should catch cx_Oracle.DatabaseError, etc.
                    return True, var, val  # we give up and assume it's a string
            
    def do_setbind(self, arg):
        '''Sets or shows values of bind (`:`) variables.'''        
        if not arg:
            return self.do_print(arg)
        assigned, var, val = self.interpret_variable_assignment(arg)
        if not assigned:
            return self.do_print(var)
        else:
            self.binds[var] = val

    def do_define(self, arg):
        '''Sets or shows values of substitution (`&`) variables.'''
        if not arg:
            for (substvar, val) in sorted(self.substvars.items()):
                self.poutput('DEFINE %s = "%s" (%s)' % (substvar, val, type(val)))
        assigned, var, val = self.interpret_variable_assignment(arg)
        if assigned:
            self.substvars[var] = val
        else:
            if var in self.substvars:
                self.poutput('DEFINE %s = "%s" (%s)' % (var, self.substvars[var], type(self.substvars[var])))
    
    def do_exec(self, arg):
        if arg.startswith(':'):
            self.do_setbind(arg.parsed.expanded.split(':',1)[1])
        else:
            varsUsed = self.findBinds(arg, {})
            try:
                self.curs.execute('begin\n%s;end;' % arg, varsUsed)
            except Exception, e:
                self.perror(e)

    '''
    Fails:
    select n into :n from test;'''
    
    def anon_plsql(self, line1):
        lines = [line1]
        while True:
            line = self.pseudo_raw_input(self.continuation_prompt)
            self.history[-1] = '%s\n%s' % (self.history[-1], line)
            if line == 'EOF':
                return
            if line.strip() == '/':
                try:
                    self.curs.execute('\n'.join(lines))
                except Exception, e:
                    self.perror(e)
                return
            lines.append(line)

    def do_begin(self, arg):
        '''
        PL/SQL blocks can be used normally in sqlpython, though enclosing statements in
        REMARK BEGIN... REMARK END statements can help with parsing speed.'''
        self.anon_plsql('begin ' + arg)

    def do_declare(self, arg):
        self.anon_plsql('declare ' + arg)
        
    def ls_where_clause(self, arg, opts):
        where = ['WHERE (1=1) ']
        if arg:
            target = arg.upper().replace('*','%')
            if target in self.object_types:
                target += '/%'
            where.append("""
                AND(   UPPER(object_type) || '/' || UPPER(object_name) LIKE '%s'
                       OR UPPER(object_name) LIKE '%s')""" % (target, target))
        if not opts.all:
            where.append("AND owner = my_own")
        return '\n'.join(where)
        
    def resolve_many(self, arg, opts):
        statement = """SELECT owner, object_name, object_type FROM (%s)
            %s""" % (metaqueries['ls'][self.rdbms], self.ls_where_clause(arg, opts))
        self._execute(statement)
        return self.curs.fetchall()

    object_types = (
        'BASE TABLE',
        'CLUSTER',              
        'CONSUMER GROUP',       
        'CONTEXT',              
        'DIRECTORY',            
        'EDITION',              
        'EVALUATION CONTEXT',   
        'FUNCTION',             
        'INDEX',                
        'INDEX PARTITION',      
        'INDEXTYPE',            
        'JAVA CLASS',           
        'JAVA DATA',            
        'JAVA RESOURCE',        
        'JOB',                  
        'JOB CLASS',            
        'LIBRARY',              
        'MATERIALIZED VIEW',    
        'OPERATOR',             
        'PACKAGE',              
        'PACKAGE BODY',         
        'PROCEDURE',            
        'PROGRAM',              
        'RULE',                 
        'RULE SET',             
        'SCHEDULE',             
        'SEQUENCE',             
        'SYNONYM',              
        'TABLE',                
        'TABLE PARTITION',      
        'TRIGGER',              
        'TYPE',                 
        'TYPE BODY',            
        'VIEW',                 
        'WINDOW',               
        'WINDOW GROUP',         
        'XML SCHEMA')
        
    def metadata(self):
        schemas = self.connections[self.connection_number]['schemas']
        username = self.connections[self.connection_number]['user'].upper()
        return (username, schemas)
        
    def _to_sql_wildcards(self, original):
        return original.replace('*','%').replace('?','_')
        #hmm... but these should be escape-able?
        
    def _to_re_wildcards(self, original):
        result = re.escape(original)
        return result.replace('\\*','.*').replace('\\?','.')
        
    def _regex(self, s, exact=False):
        seekpatt = r'[/\\]?%s[/\\]?' % (
            s.replace('*', '.*').replace('?','.').replace('%', '.*'))        
        if exact:
            seekpatt = '^%s$' % seekpatt
        return re.compile(seekpatt, re.IGNORECASE)

    @options([make_option('-a', '--all', action='store_true', help="all schemas' objects"),
              make_option('-i', '--immediate', action='store_true', help="Wait until refresh is done"),
              make_option('-c', '--check', action='store_true', help="Don't refresh, just check refresh status")])
    def do_refresh(self, arg, opts):
        '''Refreshes metadata for the specified schema; only required
           if table structures, etc. have changed. (sqlpython will check
           for new objects, and will not waste labor if no objects have
           been created or modified in a schema.)'''
        (username, schemas) = self.metadata()
        if opts.check:
            self.poutput(schemas.refresh_times(arg))
            return
        if opts.all:
            if opts.immediate:
                self.perror("Don't combine --all and --immediate.  It will take too long.")
                return
            schemas.refresh()
        elif arg:
            schemas.refresh_one(arg)
        else:
            schemas.refresh_one(username)
        
    def _matching_database_objects(self, arg, opts):
        # jrrt.p* should work even if not --all
        # doesn't get java$options
        (username, schemas) = self.metadata()
        if opts.get('immediate'):
            if opts.get('all'):
                self.perror('Cannot combine --all with --immediate - operation takes too long')
                raise StopIteration
            else:
                self.pfeedback('Refreshing metadata for %s...' % username)
                schemas.refresh_one(username)
        if schemas.complete == 0:
            self.pfeedback('No data available yet - still gathering schema information')
            raise StopIteration
        elif (opts.get('all') and (schemas.complete != 'all')):
            self.pfeedback('Results are incomplete - only %d schemas mapped so far' % schemas.complete)        
        
        seek = self._regex(arg, opts.get('exact'))
        qualified = opts.get('all')
        for (schema_name, schema) in schemas.items():
            if schema_name == username or opts.get('all'):
                for (name, dbobj) in schema.schema.items():                
                    metadata = MetaData(object_name=name, schema_name=schema_name, db_object=dbobj)
                    if (not arg) or (
                           seek.search(metadata.descriptor(qualified)) or 
                           seek.search(metadata.name(qualified)) or 
                           seek.search(metadata.db_type)):
                        yield metadata
   
    @options(standard_options)
    def do_ls(self, arg, opts):
        '''
        Lists objects as through they were in an {object_type}/{object_name} UNIX
        directory structure.  `*` and `%` may be used as wildcards.
        '''
        opts.exact = True
        (username, schemas) = self.metadata()
        result = []
        for obj in self._matching_database_objects(arg, opts):
            if opts.long:
                result.append('%s' % (obj.descriptor(qualified=True)))
                # if opts.long: status, last_ddl_time
            else:
                result.append(obj.descriptor(qualified=opts.all))
        if result:
            result.sort(reverse=bool(opts.reverse))
            self.poutput('\n'.join(result))
        
    @options([make_option('-i', '--ignore-case', dest='ignorecase', action='store_true', help='Case-insensitive search'),
              make_option('-a', '--all', action='store_true', help="all schemas' objects")])     
    
    def do_grep(self, arg, opts):
        """grep {target} {table} [{table2,...}]
        search for {target} in any of {table}'s fields"""    
        arg = self.parsed(arg)
        opts.exact = True
        args = arg.split()
        if len(args) < 2:
            self.perror(self.do_grep.__doc__)
            return
        pattern, targets = args[0], args[1:]
        if opts.ignorecase:
            pattern = pattern.lower()
            comparitor = "OR LOWER(to_char(%s)) LIKE '%%%s%%'"
        else:
            comparitor = "OR to_char(%s) LIKE '%%%s%%'"
        sql_pattern = self._to_sql_wildcards(pattern)
        re_pattern = re.compile(self._to_re_wildcards(pattern), 
                                (opts.ignorecase and re.IGNORECASE) or 0)
        for target in targets:
            for m in self._matching_database_objects(target, opts):
                self.pfeedback(m.descriptor(qualified=opts.all))
                if hasattr(m.db_object, 'columns'):
                    clauses = []
                    for col in m.db_object.columns:
                        clauses.append(comparitor % (col, sql_pattern))
                    sql = "SELECT * FROM %s WHERE 1=0\n%s;" % (m.object_name, ' '.join(clauses))
                    sql = self.parsed(sql, 
                                          terminator=arg.parsed.terminator or ';',
                                          suffix=arg.parsed.suffix)
                    self.do_select(sql)
                elif hasattr(m.db_object, 'source'):
                    for (line_num, line) in m.db_object.source:
                        if re_pattern.search(line):
                            self.poutput('%4d: %s' % (line_num, line))
                

    def _cast(self, colname, typ='CHAR'):
        'self._cast(colname, typ) => Returns the RDBMS-equivalent "CAST (colname AS typ) expression.' 
        converter = {'oracle': 'TO_%(typ)s(%(colname)s)'}.get(self.rdbms, 'CAST(%(colname)s AS %(typ)s)')
        return converter % {'colname': colname, 'typ': typ}
    
    def _execute(self, sql, bindvars={}):
        self.sqlfeedback(sql)
        self.curs.execute(sql, bindvars)

    #@options([make_option('-l', '--long', action='store_true', 
    #                      help='Wordy, easy-to-understand form'),])                
    def do_refs(self, arg):
        '''Lists referential integrity (foreign key constraints) on an object or referring to it.'''
        
        if not arg.strip():
            self.perror('Usage: refs (table name)')
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
        self.poutput('\n'.join(result) + "\n")
    
def _test():
    import doctest
    doctest.testmod()
    
if __name__ == "__main__":
    "Silent return implies that all unit tests succeeded.  Use -v to see details."
    _test()
