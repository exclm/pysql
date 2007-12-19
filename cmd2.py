"""Variant on standard library's cmd with extra features:

Searchable command history
Multi-line commands
Case-insensitive commands
Special-character shortcut commands

still to do:
environment (maxrows, etc.)
edit

"""
import cmd, re, os

class Cmd(cmd.Cmd):
    caseInsensitive = True
    multilineCommands = []
    continuationPrompt = '> '    
    shortcuts = {'?': 'help', '!': 'shell', '@': 'load'}   
    excludeFromHistory = '''run r list l history hi ed li eof'''.split()   
    defaultExtension = 'txt'
    def __init__(self, *args, **kwargs):	
        cmd.Cmd.__init__(self, *args, **kwargs)
        self.history = History()
	
    def precmd(self, line):
        """Hook method executed just before the command line is
        interpreted, but after the input prompt is generated and issued.
        
        Makes commands case-insensitive (but unfortunately does not alter command completion).
        """
        try:
            (command, args) = line.split(None,1)
	except ValueError:
	    (command, args) = line, ''
	if self.caseInsensitive:
	    command = command.lower()
	statement = ' '.join([command, args])
	if (not self.multilineCommands) or (command not in self.multilineCommands):
	    return statement
	return self.finishStatement(statement)

    def postcmd(self, stop, line):
        """Hook method executed just after a command dispatch is finished."""
	try:
	    command = line.split(None,1)[0].lower()
	    if command not in self.excludeFromHistory:
		self.history.append(line)
	finally:
	    return stop
	
    def finishStatement(self, firstline):
	statement = firstline
	while not self.statementHasEnded(statement):
	    statement = '%s\n%s' % (statement, self.pseudo_raw_input(self.continuationPrompt))
	return statement
	# assembling a list of lines and joining them at the end would be faster, 
	# but statementHasEnded needs a string arg; anyway, we're getting
	# user input and users are slow.
	
    def pseudo_raw_input(self, prompt):
	"""copied from cmd's cmdloop; like raw_input, but accounts for changed stdin, stdout"""
	
	if self.use_rawinput:
	    try:
		line = raw_input(prompt)
	    except EOFError:
		line = 'EOF'
	else:
	    self.stdout.write(prompt)
	    self.stdout.flush()
	    line = self.stdin.readline()
	    if not len(line):
		line = 'EOF'
	    else:
		line = line[:-1] # chop \n
	return line
			    
    def do_EOF(self, arg):
	return True
    do_eof = do_EOF
    
    statementEndPattern = re.compile(r'[\n;]\s*$')	
    def statementHasEnded(self, lines):
	"""This version lets statements end with ; or with a blank line.
	Override for your own needs."""
	return bool(self.statementEndPattern.search(lines))
	       
    def parseline(self, line):
        """Parse the line into a command name and a string containing
        the arguments.  Returns a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.
        """
        line = line.strip()
        if not line:
            return None, None, line
	shortcut = self.shortcuts.get(line[0])
	if shortcut and hasattr(self, 'do_%s' % shortcut):
	    line = '%s %s' % (shortcut, line[1:])
        i, n = 0, len(line)
        while i < n and line[i] in self.identchars: i = i+1
        cmd, arg = line[:i], line[i:].strip()
        return cmd, arg, line
    
    def do_shell(self, arg):
        'execute a command as if at the OS prompt.'
        os.system(arg)
	
    def do_history(self, arg):
        """history [arg]: lists past commands issued
        
        no arg -> list all
        arg is integer -> list one history item, by index
        arg is string -> string search
        arg is /enclosed in forward-slashes/ -> regular expression search
        """
        if arg:
            history = self.history.get(arg)
        else:
            history = self.history
        for hi in history:
            self.stdout.write(hi.pr())
    def last_matching(self, arg):
        try:
            if arg:
                return self.history.get(arg)[-1]
            else:
                return self.history[-1]
        except:
            return None        
    def do_list(self, arg):
        """list [arg]: lists last command issued
        
        no arg -> list absolute last
        arg is integer -> list one history item, by index
        - arg, arg - (integer) -> list up to or after #arg
        arg is string -> list last command matching string search
        arg is /enclosed in forward-slashes/ -> regular expression search
        """
        try:
            self.stdout.write(self.last_matching(arg).pr())
        except:
            pass
    do_hi = do_history
    do_l = do_list
    do_li = do_list
    
    def breakupStatements(self, txt):
	"""takes text that may include multiple statements and 
	breaks it into a list of individual statements."""
	result = ['']
	for line in txt.splitlines():
	    result[-1] += line
	    if self.statementHasEnded(result[-1]):
		result.append('')
	
    def do_load(self, fname):
        """Runs command(s) from a file."""
	stdin = self.stdin
	try:
	    self.stdin = open(fname, 'r')
        except IOError, e:
            try:
                self.stdin = open('%s.%s' % (fname, self.defaultExtension), 'r')
            except:
                print 'Problem opening file %s: \n%s' % (fname, e)
		self.stdin = stdin
                return 	    
	use_rawinput = self.use_rawinput
	self.use_rawinput = False
	self.cmdloop()
	self.stdin.close()
	self.stdin = stdin
	self.use_rawinput = use_rawinput
	self.stdin.flush()
	self.lastcmd = ''

class HistoryItem(str):
    def __init__(self, instr):
        str.__init__(self, instr)
        self.lowercase = self.lower()
        self.idx = None
    def pr(self):
	return '-------------------------[%d]\n%s\n' % (self.idx, str(self))
        
class History(list):
    rangeFrom = re.compile(r'^([\d])+\s*\-$')
    def append(self, new):
        new = HistoryItem(new)
        list.append(self, new)
        new.idx = len(self)
    def extend(self, new):
        for n in new:
            self.append(n)
    def get(self, getme):
        try:
            getme = int(getme)
            if getme < 0:
                return self[:(-1 * getme)]
            else:
                return [self[getme-1]]
        except IndexError:
            return []
        except (ValueError, TypeError):
            getme = getme.strip()
            mtch = self.rangeFrom.search(getme)
            if mtch:
                return self[(int(mtch.group(1))-1):]
            if getme.startswith(r'/') and getme.endswith(r'/'):
                finder = re.compile(getme[1:-1], re.DOTALL | re.MULTILINE | re.IGNORECASE)
                def isin(hi):
                    return finder.search(hi)
            else:
                def isin(hi):
                    return (getme.lower() in hi.lowercase)
            return [itm for itm in self if isin(itm)]

    
	
