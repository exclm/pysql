import unittest, sys, tempfile, re, os.path, pyparsing
from sqlpyPlus import *

class Borg(object):
    # from Python Cookbook, 2nd Ed., recipe 6.16
    _shared_state = {}
    def __new__(cls, *a, **k):
        obj = object.__new__(cls, *a, **k)
        obj.__dict__ = cls._shared_state
        return obj
    
class OutputTrap(Borg):
    old_stdout = sys.stdout
    def __init__(self):
        self.trap = tempfile.TemporaryFile()
        sys.stdout = self.trap
    def dump(self):
        self.trap.seek(0)
        result = self.trap.read()
        self.trap.close()
        self.trap = tempfile.TemporaryFile()
        sys.stdout = self.trap
        return result
    def teardown(self):
        sys.stdout = self.old_stdout

class TestSqlPyPlus(unittest.TestCase):
    transcriptReader = re.compile('testdata@eqdev> (.*?)\n(.*?)(?=testdata@eqdev>)', re.DOTALL)
    transcriptFileName = 'test_sqlpyPlus.txt'
    def setUp(self):
        self.outputTrap = OutputTrap()
        transcriptFile = open(self.transcriptFileName)
        self.transcript = transcriptFile.read()
        transcriptFile.close()
        self.directives = self.transcriptReader.finditer(self.transcript)        
        self.testsession = sqlpyPlus()
        self.testsession.onecmd('connect ' + connectString)
        self.transcriptReader = re.compile(
            '%s(.*?)\n\n(.*?)(?=%s)' % (self.testsession.prompt, self.testsession.prompt), re.DOTALL)
        self.commandCleaner = '\n%s' % (self.testsession.continuationPrompt)
    def assertOutput(self, commandtext, expected, lineNum):
        self.testsession.onecmd(commandtext)
        result = self.outputTrap.dump()
        self.assertEqual(expected.strip(), result.strip(), 
            '\nFile %s, line %d\nCommand was:\n%s\nExpected:\n%s\nGot:\n%s\n' % 
            (self.transcriptFileName, lineNum, commandtext, expected, result))
    def testall(self):
        for directive in self.directives:
            (command, result) = directive.groups()
            command = command.replace(self.commandCleaner, '\n')
            self.assertOutput(command, result, lineNum=self.transcript.count('\n', 0, directive.start()))
    def tearDown(self):
        self.outputTrap.teardown()

try:        
    connectString = sys.argv.pop(1)
except IndexError:
    print 'Usage: python %s username/password@oracleSID' % os.path.split(__file__)[-1]
    sys.exit()
unittest.main()


def transcript(cmdapp, filename='test_sqlpyPlus.txt'):
    tfile = open(filename)
    txt = tfile.read()
    tfile.close()
    prompt = pyparsing.Suppress(pyparsing.lineStart + cmd.prompt)
    continuationPrompt = pyparsing.Suppress(pyparsing.lineStart + cmd.continuationPrompt)
    cmdtxtPattern = (prompt + pyparsing.restOfLine + pyparsing.ZeroOrMore(
        pyparsing.lineEnd + continuationPrompt + pyparsing.restOfLine))("command")
    previousStartPoint = 0
    results = []
    for onecmd in cmdtxtPattern.scanString(txt):
        if len(results) > 0:
            results[-1]['response'] = txt[previousStartPoint:onecmd[1]]
        results.append({'command': ''.join(onecmd[0].command), 'response': txt[onecmd[2]:]})
        previousStartPoint = onecmd[2]