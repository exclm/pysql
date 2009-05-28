#
# SqlPython V1.6.5.1
# Author: Luca.Canali@cern.ch, Apr 2006
# Rev 1-May-09
#
# A python module to reproduce Oracle's command line 'sqlplus-like' within python
# Intended to allow easy customizations and extentions 
# Best used with the companion modules sqlpyPlus and mysqlpy 
# See also http://twiki.cern.ch/twiki/bin/view/PSSGroup/SqlPython

import cmd2,getpass,binascii,cx_Oracle,re,os
import sqlpyPlus, sqlalchemy, pyparsing
__version__ = '1.6.5.1'    

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

    
class sqlpython(cmd2.Cmd):
    '''A python module to reproduce Oracle's command line with focus on customization and extention'''

    def __init__(self):
        cmd2.Cmd.__init__(self)
        self.no_connection()
        self.maxfetch = 1000
        self.terminator = ';'
        self.timeout = 30
        self.commit_on_exit = True
        self.connections = {}
        
    def no_connection(self):
        self.prompt = 'SQL.No_Connection> '
        self.curs = None
        self.conn = None
        self.connection_number = None
        
    def make_connection_current(self, connection_number):
        self.conn = self.connections[connection_number]['conn']
        self.prompt = self.connections[connection_number]['prompt']
        self.rdbms = self.connections[connection_number]['rdbms']
        self.connection_number = connection_number
        self.curs = self.conn.cursor()
            
    def successful_connection_to_number(self, arg):
        try:
            connection_number = int(arg)
        except ValueError:            
            return False
        self.make_connection_current(connection_number)
        if (self.rdbms == 'oracle') and self.serveroutput:
            self.curs.callproc('dbms_output.enable', [])           
        return True

    def list_connections(self):
        self.stdout.write('Existing connections:\n')
        self.stdout.write('\n'.join('%s (%s)' % (v['prompt'], v['rdbms']) 
                                    for (k,v) in sorted(self.connections.items())) + '\n')
        
    def disconnect(self, arg):
        try:
            connection_number = int(arg)
            connection = self.connections[connection_number]
        except (ValueError, KeyError):
            self.list_connections()
            return
        if self.commit_on_exit:
            connection['conn'].commit()
        self.connections.pop(connection_number)
        if connection_number == self.connection_number:
            self.no_connection()
            
    def closeall(self):
        for connection_number in self.connections.keys():
            self.disconnect(connection_number)
        self.curs = None
        self.no_connection()        
            
    def url_connect(self, arg):
        eng = sqlalchemy.create_engine(arg) 
        self.conn = eng.connect().connection
        conn  = {'conn': self.conn, 'prompt': self.prompt, 'dbname': eng.url.database,
                 'rdbms': eng.url.drivername, 'user': eng.url.username or '', 
                 'eng': eng}
        return conn
    def ora_connect(self, arg):
        modeval = 0
        oraserv = None
        for modere, modevalue in self.connection_modes.items():
            if modere.search(arg):
                arg = modere.sub('', arg)
                modeval = modevalue
        try:
            orauser, oraserv = arg.split('@')
        except ValueError:
            try:
                oraserv = os.environ['ORACLE_SID']
            except KeyError:
                self.perror('instance not specified and environment variable ORACLE_SID not set')
                return
            orauser = arg
        sid = oraserv
        try:
            host, sid = oraserv.split('/')
            try:
                host, port = host.split(':')
                port = int(port)
            except ValueError:
                port = 1521
            oraserv = cx_Oracle.makedsn(host, port, sid)
        except ValueError:
            pass
        try:
            orauser, orapass = orauser.split('/')
        except ValueError:
            orapass = getpass.getpass('Password: ')
        if orauser.upper() == 'SYS' and not modeval:
            self.pfeedback('Privilege not specified for SYS, assuming SYSOPER')
            modeval = cx_Oracle.SYSOPER
        result = self.url_connect('oracle://%s:%s@%s/?mode=%d' % (orauser, orapass, oraserv, modeval))
        result['dbname'] = oraserv
        return result
    
    connection_modes = {re.compile(' AS SYSDBA', re.IGNORECASE): cx_Oracle.SYSDBA, 
                        re.compile(' AS SYSOPER', re.IGNORECASE): cx_Oracle.SYSOPER}
    @cmd2.options([cmd2.make_option('-a', '--add', action='store_true', 
                                    help='add connection (keep current connection)'),
                   cmd2.make_option('-c', '--close', action='store_true', 
                                    help='close connection {N} (or current)'),
                   cmd2.make_option('-C', '--closeall', action='store_true', 
                                    help='close all connections'),])
    def do_connect(self, arg, opts):
        '''Opens the DB connection'''
        if opts.closeall:
            self.closeall()
            return
        if opts.close:
            if not arg:
                arg = self.connection_number
            self.disconnect(arg)
            return
        if not arg:
            self.list_connections()
            return
        try:
            if self.successful_connection_to_number(arg):
                return
        except IndexError:
            self.list_connections()
            return
        try:
            connect_info = self.url_connect(arg)
        except sqlalchemy.exc.ArgumentError, e:
            connect_info = self.ora_connect(arg)
        if opts.add or (self.connection_number is None):
            try:
                self.connection_number = max(self.connections.keys()) + 1
            except ValueError:
                self.connection_number = 0
        connect_info['prompt'] = '%d:%s@%s> ' % (self.connection_number, connect_info['user'], connect_info['dbname'])
        self.connections[self.connection_number] = connect_info
        self.make_connection_current(self.connection_number)
        self.curs = self.conn.cursor()
        if (self.rdbms == 'oracle') and self.serveroutput:
            self.curs.callproc('dbms_output.enable', [])
        if (self.rdbms == 'mysql'):
            self.curs.execute('SET SQL_MODE=ANSI')
    def postparsing_precmd(self, statement):
        stop = 0
        self.saved_connection_number = None
        if statement.parsed.connection_number:
            saved_connection_number = self.connection_number
            try:
                if self.successful_connection_to_number(statement.parsed.connection_number):
                    if statement.parsed.command:
                        self.saved_connection_number = saved_connection_number
            except KeyError:
                self.list_connections()
                raise KeyError, 'No connection #%s' % statement.parsed.connection_number
        return stop, statement           
    def postparsing_postcmd(self, stop):
        if self.saved_connection_number is not None:
            self.successful_connection_to_number(self.saved_connection_number)
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
                   'postgres': Parser(pyparsing.Literal('%(') + 
                                      pyparsing.Word(pyparsing.alphanums + "_$#") + ')s')}
    def findBinds(self, target, givenBindVars = {}):
        result = givenBindVars
        if self.rdbms in self.bindScanner:
            for finding, startat, endat in self.bindScanner[self.rdbms].scanner.scanString(target):
                varname = finding[1]
                try:
                    result[varname] = self.binds[varname]
                except KeyError:
                    if not givenBindVars.has_key(varname):
                        print 'Bind variable %s not defined.' % (varname)
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
        self.curs.execute(command % (arg.parsed.command, arg.parsed.args), self.varsUsed)
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
    colorcodes = {'bold':{True:'\x1b[1m',False:'\x1b[22m'},
                  'red':{True:'\x1b[36m',False:'\x1b[39m'},
                  'cyan':{True:'\x1b[31m',False:'\x1b[39m'},
                  'underline':{True:'\x1b[4m',False:'\x1b[24m'}}
    colors = True
    def colorize(self, val, color):
        if self.colors and (self.stdout == self.initial_stdout):
            if color not in self.colorcodes:
                if (color % 2):
                    color = 'red'
                else:
                    color = 'cyan'
            return self.colorcodes[color][True] + val + self.colorcodes[color][False]        
        return val
    def pmatrix(self,rows,desc,maxlen=30,heading=True,restructuredtext=False):
        '''prints a matrix, used by sqlpython to print queries' result sets'''
        names = []
        maxen = []
        toprint = []
        for d in desc:
            n = d[0]
            names.append(n)      # list col names
            maxen.append(len(n)) # col length
        rcols = range(len(desc))
        rrows = range(len(rows))
        for i in rrows:          # loops for all rows
            rowsi = map(str, rows[i]) # current row to process
            split = []                # service var is row split is needed
            mustsplit = 0             # flag 
            for j in rcols:
                if str(desc[j][1]) == "<type 'cx_Oracle.BINARY'>":  # handles RAW columns
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
                if str(desc[i][1]) == "<type 'cx_Oracle.NUMBER'>":  # right align numbers
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
    
    
    
    

