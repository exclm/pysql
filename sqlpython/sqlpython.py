#
# SqlPython V1.6.7
# Author: Luca.Canali@cern.ch, Apr 2006
# Rev 2-Sep-09

# A python module to reproduce Oracle's command line 'sqlplus-like' within python
# Intended to allow easy customizations and extentions 
# Best used with the companion modules sqlpyPlus and mysqlpy 
# See also http://twiki.cern.ch/twiki/bin/view/PSSGroup/SqlPython

import cmd2,getpass,binascii,re,os,platform
import pyparsing, connections
__version__ = '1.7.0'
try:
    import cx_Oracle
except ImportError:
    cx_Oracle = None
try:
    import psycopg2
except ImportError:
    psycopg2 = None

class Parser(object):
    comment_def = "--" + pyparsing.NotAny('-' + pyparsing.CaselessKeyword('begin')) + pyparsing.ZeroOrMore(pyparsing.CharsNotIn("\n"))    
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

    
class sqlpython(cmd2.Cmd):
    '''A python module to reproduce Oracle's command line with focus on customization and extention'''

    def __init__(self):
        cmd2.Cmd.__init__(self)
        self.no_instance()
        self.maxfetch = 1000
        self.terminator = ';'
        self.timeout = 30
        self.commit_on_exit = True
        self.instances = {}
        
    def no_instance(self):
        self.prompt = 'SQL.No_Connection> '
        self.curs = None
        self.current_instance = None
        self.instance_number = None
        
    def make_instance_current(self, instance_number):
        db_instance = self.instances[instance_number]
        self.prompt = db_instance.prompt
        self.rdbms = db_instance.rdbms
        self.instance_number = instance_number
        self.curs = db_instance.connection.cursor()
        self.current_instance = db_instance
            
    def list_instances(self):
        self.stdout.write('Existing connections:\n')
        self.stdout.write('\n'.join('%s (%s)' % (v.prompt, v.rdbms) 
                                    for (k,v) in sorted(self.instances.items())) + '\n')
        
    def disconnect(self, arg):
        try:
            instance_number = int(arg)
            instance = self.instances[instance_number]
        except (ValueError, KeyError):
            self.list_instances()
            return
        if self.commit_on_exit:
            instance.connection.commit()
        self.instances.pop(instance_number)
        if instance_number == self.instance_number:
            self.no_instance()
            
    def closeall(self):
        for instance_number in self.instances.keys():
            self.disconnect(instance_number)
        self.curs = None
        self.no_instance()        
            
    legal_sql_word = pyparsing.Word(pyparsing.alphanums + '_$#')
          
    def successfully_connect_to_number(self, arg):
        try:
            instance_number = int(arg)
        except ValueError:            
            return False
        try:
            self.make_instance_current(instance_number)
        except IndexError:
            self.list_instances()
            return False
        if (self.rdbms == 'oracle') and self.serveroutput:
            self.curs.callproc('dbms_output.enable', [])           
        return True

    @cmd2.options([cmd2.make_option('-a', '--add', action='store_true',
                                    help='add connection (keep current connection)'),
                   cmd2.make_option('-c', '--close', action='store_true',
                                    help='close connection {N} (or current)'),
                   cmd2.make_option('-C', '--closeall', action='store_true',
                                    help='close all connections'),
                   cmd2.make_option('--postgres', action='store_true', help='Connect to postgreSQL: `sqlpython --postgres [DBNAME [USERNAME]]`'),
                   cmd2.make_option('--oracle', action='store_true', help='Connect to an Oracle database'),
                   cmd2.make_option('--mysql', action='store_true', help='Connect to a MySQL database'),
                   cmd2.make_option('-H', '--hostname', type='string',
                                    help='Machine where database is hosted'),
                   cmd2.make_option('-p', '--port', type='int',
                                    help='Port to connect to'),
                   cmd2.make_option('--password', type='string',
                                    help='Password'),
                   cmd2.make_option('-d', '--database', type='string',
                                    help='Database name to connect to'),
                   cmd2.make_option('-U', '--username', type='string',
                                    help='Database user name to connect as')])
    def do_connect(self, arg, opts):
 
        '''Opens the DB connection'''
        if opts.closeall:
            self.closeall()
            return 
        if opts.close:
            if not arg:
                arg = self.instance_number
            self.disconnect(arg)
            return 
        if (not arg) and (not opts.postgres) and (not opts.mysql):
            self.list_instances()
            return 
        if self.successfully_connect_to_number(arg):
            return
        
        db_instance = connections.DatabaseInstance(arg, opts, default_rdbms = self.default_rdbms)
        if opts.add or (self.instance_number is None):
            try:
                self.instance_number = max(self.instances.keys()) + 1
            except ValueError:
                self.instance_number = 0            
        db_instance.set_instance_number(self.instance_number)
        self.instances[self.instance_number] = db_instance
        self.make_instance_current(self.instance_number)        
        if (self.rdbms == 'oracle') and self.serveroutput:
            self.current_instance.connection.cursor().callproc('dbms_output.enable',[])
            #self.curs.callproc('dbms_output.enable', [])        
    
    def do_pickle(self, arg):
        self.current_instance.pickle()
        
    def postparsing_precmd(self, statement):
        stop = 0
        self.saved_instance_number = None
        if statement.parsed.instance_number:
            saved_instance_number = self.instance_number
            try:
                if self.successfully_connect_to_number(statement.parsed.instance_number):
                    if statement.parsed.command:
                        self.saved_instance_number = saved_instance_number
            except KeyError:
                self.list_instances()
                raise KeyError, 'No connection #%s' % statement.parsed.instance_number
        return stop, statement           
    def postparsing_postcmd(self, stop):
        if self.saved_instance_number is not None:
            self.successfully_connect_to_number(self.saved_instance_number)
        return stop
                
    do_host = cmd2.Cmd.do_shell
    
    def emptyline(self):
        pass

    def _show_errors(self, all_users=False, limit=None, mintime=None, targets=[]):
        if all_users:
            user = ''
        else:
            user = "AND ao.owner = user\n"
        if targets:
            target = 'AND (%s)\n' % ' OR '.join("ae.type || '/' || ae.name LIKE '%s'" % 
                                              t.upper().replace('*','%') for t in targets)
        else:
            target = ''
        self.curs.execute('''
            SELECT ae.owner, ae.name, ae.type, ae.position, ae.line, ae.attribute, 
                   ae.text error_text,
                   src.text object_text,
                   ao.last_ddl_time
            FROM   all_errors ae
            JOIN   all_objects ao ON (    ae.owner = ao.owner
                                      AND ae.name = ao.object_name
                                      AND ae.type = ao.object_type)
            JOIN   all_source src ON (    ae.owner = src.owner
                                      AND ae.name = src.name
                                      AND ae.type = src.type
                                      AND ae.line = src.line)
            WHERE 1=1
            %s%sORDER BY ao.last_ddl_time DESC''' % (user, target))
        if limit is None:
            errors = self.curs.fetchall()
        else:
            errors = self.curs.fetchmany(numRows = limit)
        for err in errors:
            if (mintime is not None) and (err[8] < mintime):
                break
            self.poutput('%s at line %d of %s %s.%s:' % (err[5], err[4], err[2], err[0], err[1]))
            self.poutput(err[7])
            self.poutput((' ' * (err[3]-1)) + '^')
            self.poutput(err[6])
            self.poutput('\n')
            
    def current_database_time(self):
        self.curs.execute('select sysdate from dual')
        return self.curs.fetchone()[0]
        
    def do_terminators(self, arg):
        """;    standard Oracle format
\\c   CSV (with headings)
\\C   CSV (no headings)
\\g   list
\\G   aligned list
\\h   HTML table
\\i   INSERT statements
\\j   JSON
\\r   ReStructured Text
\\s   CSV (with headings)
\\S   CSV (no headings)
\\t   transposed
\\x   XML
\\l   line plot, with markers
\\L   scatter plot (no lines)
\\b   bar graph
\\p   pie chart"""
        self.poutput(self.do_terminators.__doc__)
    
    terminatorSearchString = '|'.join('\\' + d.split()[0] for d in do_terminators.__doc__.splitlines())
        
    bindScanner = {'oracle': Parser(pyparsing.Literal(':') + pyparsing.Word( pyparsing.alphanums + "_$#" )),
                   'postgres': Parser(pyparsing.Literal('%(') + legal_sql_word + ')s')}
    def findBinds(self, target, givenBindVars = {}):
        result = givenBindVars
        #TODO: A consistent bind style?  As a setting, perhaps?
        if self.rdbms in self.bindScanner:
            for finding, startat, endat in self.bindScanner[self.rdbms].scanner.scanString(target):
                varname = finding[1]
                try:
                    result[varname] = self.binds[varname]
                except KeyError:
                    if not givenBindVars.has_key(varname):
                        raise KeyError, 'Bind variable "%s" not defined.' % (varname)
        return result

    def default(self, arg):
        self.varsUsed = self.findBinds(arg, givenBindVars={})
        ending_args = arg.lower().split()[-2:]
        if 'end' in ending_args:
            command = '%s %s;'
        else:
            command = '%s %s'    
        if self.rdbms == 'oracle':
            current_time = self.current_database_time()
        commandstring = command % (arg.parsed.command, arg.parsed.args)
        self.curs.execute(commandstring, self.varsUsed)
        executionmessage = '\nExecuted%s\n' % ((self.curs.rowcount > 0) and ' (%d rows)' % self.curs.rowcount or '')
        if self.rdbms == 'oracle':
            self._show_errors(all_users=True, limit=1, mintime=current_time)
        self.pfeedback(executionmessage)
            
    def do_commit(self, arg=''):
        self.default(self.parsed('commit %s;' % (arg)))
    def do_rollback(self, arg=''):
        self.default(self.parsed('rollback %s;' % (arg)))
    def do_quit(self, arg):
        if self.commit_on_exit:
            self.closeall()
        return cmd2.Cmd.do_quit(self, None)
    do_exit = do_quit
    do_q = do_quit
    def colorize(self, val, color):
        if color not in self.colorcodes:
            if (color % 2):
                color = 'red'
            else:
                color = 'cyan'
        return cmd2.Cmd.colorize(self, val, color)
    def pmatrix(self,rows,maxlen=30,heading=True,restructuredtext=False):
        '''prints a matrix, used by sqlpython to print queries' result sets'''
        names = self.colnames
        maxen = [len(n) for n in self.colnames]
        toprint = []
        rcols = range(len(self.colnames))
        rrows = range(len(rows))
        for i in rrows:          # loops for all rows
            rowsi = map(str, rows[i]) # current row to process
            split = []                # service var is row split is needed
            mustsplit = 0             # flag 
            for j in rcols:
                if str(self.coltypes[j]) == "<type 'cx_Oracle.BINARY'>":  # handles RAW columns
                    rowsi[j] = binascii.b2a_hex(rowsi[j])
                maxen[j] = max(maxen[j], len(rowsi[j]))    # computes max field length
                if maxen[j] <= maxlen:
                    split.append('')
                else:                    # split the line is 2 because field is too long
                    mustsplit = 1   
                    maxen[j] = maxlen
                    split.append(rowsi[j][maxlen-1:2*maxlen-1])
                    rowsi[j] = rowsi[j][0:maxlen-1] # this implem. truncates after maxlen*2
            toprint.append(rowsi)        # 'toprint' is a printable copy of rows
            if mustsplit != 0:
                toprint.append(split)
        sepcols = []
        for i in rcols:
            maxcol = maxen[i]
            name = names[i]
            sepcols.append("-" * maxcol)  # formats column names (header)
            names[i] = name + (" " * (maxcol-len(name))) # formats separ line with --
            rrows2 = range(len(toprint))
            for j in rrows2:
                val = toprint[j][i]
                if str(self.coltypes[i]) == "<type 'cx_Oracle.NUMBER'>":  # right align numbers - but must generalize!
                    toprint[j][i] = (" " * (maxcol-len(val))) + val
                else:
                    toprint[j][i] = val + (" " * (maxcol-len(val)))
                toprint[j][i] = self.colorize(toprint[j][i], i)
        for j in rrows2:
            toprint[j] = ' '.join(toprint[j])
        names = [self.colorize(name, n) for (n, name) in enumerate(names)]
        names = ' '.join(names)
        names = self.colorize(names, 'bold')
        sepcols = ' '.join(sepcols)
        if heading or restructuredtext:
            toprint.insert(0, sepcols)
            toprint.insert(0, names)
        if restructuredtext:
            toprint.insert(0, sepcols)
            toprint.append(sepcols)
        return '\n'.join(toprint)
    
    
    
    

