import cmd2

class test(cmd2.Cmd):
    binarypar = True
    def do_sing(self, arg):
        '''Sings.  
        
        Hums if it has to fake it.'''
        print arg or 'hmm hmm hmm'
    def do_shout(self, arg):
        print arg.upper()
    def do_quit(self, arg):
        return 1
    multilineCommands = ['shout']

t = test()
t.cmdloop()