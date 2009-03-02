#
# SqlPython V1.6.0
# Author: Luca.Canali@cern.ch, Apr 2006
# Rev 25-Feb-09
#
# A python module to reproduce Oracle's command line 'sqlplus-like' within python
# Intended to allow easy customizations and extentions 
# Best used with the companion modules sqlpyPlus and mysqlpy 
# See also http://twiki.cern.ch/twiki/bin/view/PSSGroup/SqlPython

import cmd2,getpass,binascii,cx_Oracle,re,os
import sqlpyPlus
__version__ = '1.6.0'    

class sqlpython(cmd2.Cmd):
    '''A python module to reproduce Oracle's command line with focus on customization and extention'''

    def __init__(self):
        cmd2.Cmd.__init__(self)
        self.prompt = 'SQL.No_Connection> '
        self.maxfetch = 1000
        self.terminator = ';'
        self.timeout = 30
        self.commit_on_exit = True
        
    connection_modes = {re.compile(' AS SYSDBA', re.IGNORECASE): cx_Oracle.SYSDBA, 
                        re.compile(' AS SYSOPER', re.IGNORECASE): cx_Oracle.SYSOPER}
    def do_connect(self, arg):
        '''Opens the DB connection'''
        modeval = 0
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
                print 'instance not specified and environment variable ORACLE_SID not set'
                return
            orauser = arg
        self.sid = oraserv
        try:
            host, self.sid = oraserv.split('/')
            try:
                host, port = host.split(':')
                port = int(port)
            except ValueError:
                port = 1521
            oraserv = cx_Oracle.makedsn(host, port, self.sid)
        except ValueError:
            pass
        try:
            orauser, orapass = orauser.split('/')
        except ValueError:
            orapass = getpass.getpass('Password: ')
        if orauser.upper() == 'SYS' and not modeval:
            print 'Privilege not specified for SYS, assuming SYSOPER'
            modeval = cx_Oracle.SYSOPER
        try:
            self.orcl = cx_Oracle.connect(orauser,orapass,oraserv,modeval)
            self.curs = self.orcl.cursor()
            self.prompt = '%s@%s> ' % (orauser, self.sid)
        except Exception, e:
            print e
            
    
    def emptyline(self):
        pass
                           
    def do_terminators(self, arg):
        """;    standard Oracle format
\\c   CSV (with headings)
\\C   CSV (no headings)
\\g   list
\\G   aligned list
\\h   HTML table
\\i   INSERT statements
\\s   CSV (with headings)
\\S   CSV (no headings)
\\t   transposed
\\x   XML
\\l   line plot, with markers
\\L   scatter plot (no lines)
\\b   bar graph
\\p   pie chart"""
        print self.do_terminators.__doc__
    
    terminatorSearchString = '|'.join('\\' + d.split()[0] for d in do_terminators.__doc__.splitlines())
        
    def default(self, arg):
        self.varsUsed = sqlpyPlus.findBinds(arg, self.binds, givenBindVars={})
        self.curs.execute('%s %s' % (arg.parsed.command, arg.parsed.args), self.varsUsed)            
        print '\nExecuted%s\n' % ((self.curs.rowcount > 0) and ' (%d rows)' % self.curs.rowcount or '')
            
    def do_commit(self, arg=''):
        self.default(self.parsed('commit %s;' % (arg)))
    def do_rollback(self, arg=''):
        self.default(self.parsed('rollback %s;' % (arg)))
    def do_quit(self, arg):
        if self.commit_on_exit and hasattr(self, 'curs'):
            self.default(self.parsed('commit'))
        return cmd2.Cmd.do_quit(self, None)
    do_exit = do_quit
    do_q = do_quit
    
def pmatrix(rows,desc,maxlen=30,heading=True):
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
    for j in rrows2:
        toprint[j] = ' '.join(toprint[j])
    names = ' '.join(names)
    sepcols = ' '.join(sepcols)
    if heading:
        toprint.insert(0, sepcols)
        toprint.insert(0, names)
    return '\n'.join(toprint)

