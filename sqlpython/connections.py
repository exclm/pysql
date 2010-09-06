import re
import os
import getpass
import gerald
import time
import optparse
import doctest
import pyparsing

gerald_classes = {}

try:
    import cx_Oracle
    gerald_classes['oracle'] = gerald.oracle_schema.User
except ImportError:
    pass

try:
    import psycopg2
    gerald_classes['postgres'] = gerald.PostgresSchema
except ImportError:
    pass

try:
    import MySQLdb
    gerald_classes['mysql'] = gerald.MySQLSchema
except ImportError:
    pass

#if not gerald_classes:
#    raise ImportError, 'No Python database adapters installed!'

class ObjectDescriptor(object):
    def __init__(self, name, dbobj):
        self.fullname = name
        self.dbobj = dbobj
        if hasattr(self.dbobj, 'type'):
            self.type = self.dbobj.type.lower()
        else:
            self.type = str(type(self.dbobj)).split('.')[-1].lower().strip("'>")
        self.path = '%s/%s' % (self.type, self.fullname)
        if '.' in self.fullname:
            (self.owner, self.unqualified_name) = self.fullname.split('.')
            self.owner = self.owner.lower()        
        else:
            (self.owner, self.unqualified_name) = (None, self.fullname)        
        self.unqualified_path = '%s/%s' % (self.type, self.unqualified_name)
    def match_pattern(self, pattern, specific_owner=None):
        right_owner = (not self.owner) or (not specific_owner) or (self.owner == specific_owner.lower())
        if not pattern:
            return right_owner        
        compiled = re.compile(pattern, re.IGNORECASE)            
        if r'\.' in pattern:
            return compiled.match(self.fullname) or compiled.match(self.path)
        return right_owner and (compiled.match(self.type) or 
                                compiled.match(self.type + r'/') or
                                 compiled.match(self.unqualified_name) or
                                 compiled.match(self.unqualified_path))
        
class OptionTestDummy(object):
    mysql = None
    postgres = None
    username = None
    password = None
    hostname = None
    port = None
    database = None
    mode = 0
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)
        
class DatabaseInstance(object):
    username = None
    password = None
    hostname = None
    port = None
    database = None
    mode = 0
    connection_uri_parser = re.compile('(?P<rdbms>postgres|oracle|mysql|sqlite|mssql)://?(?P<connect_string>.*$)', re.IGNORECASE)    
    connection_parser = re.compile('((?P<database>\S+)(\s+(?P<username>\S+))?)?')    
    def __init__(self, arg, opts, default_rdbms = 'oracle'):
        'no docstring'
        '''
        >>> opts = OptionTestDummy(postgres=True, password='password')        
        >>> DatabaseInstance('thedatabase theuser', opts).uri()        
        'postgres://theuser:password@localhost:5432/thedatabase'
        >>> opts = OptionTestDummy(password='password')
        >>> DatabaseInstance('oracle://user:password@db', opts).uri()        
        'oracle://user:password@db'
        >>> DatabaseInstance('user/password@db', opts).uri()
        'oracle://user:password@db'
        >>> DatabaseInstance('user/password@db as sysdba', opts).uri()
        'oracle://user:password@db?mode=2'
        >>> DatabaseInstance('user/password@thehost/db', opts).uri()        
        'oracle://user:password@thehost:1521/db'
        >>> opts = OptionTestDummy(postgres=True, hostname='thehost', password='password')
        >>> DatabaseInstance('thedatabase theuser', opts).uri()        
        'postgres://theuser:password@thehost:5432/thedatabase'
        >>> opts = OptionTestDummy(mysql=True, password='password')
        >>> DatabaseInstance('thedatabase theuser', opts).uri()        
        'mysql://theuser:password@localhost:3306/thedatabase'
        >>> opts = OptionTestDummy(mysql=True, password='password')
        >>> DatabaseInstance('thedatabase', opts).uri()        
        'mysql://cat:password@localhost:3306/thedatabase'
        '''
        self.arg = arg
        self.opts = opts
        self.default_rdbms = default_rdbms
        self.determine_rdbms()
        if not self.parse_connect_uri(arg):
            self.set_defaults()        
            connectargs = self.connection_parser.search(self.arg)
            if connectargs:
                for param in ('username', 'password', 'database', 'port', 'hostname', 'mode'):
                    if hasattr(opts, param) and getattr(opts, param):
                        setattr(self, param, getattr(opts, param))
                    else:
                        try:
                            if connectargs.group(param):
                                setattr(self, param, connectargs.group(param))
                        except IndexError:
                            pass
        self.set_corrections()     
        if not self.password:
            self.password = getpass.getpass()    
        #self.connect()
    def parse_connect_uri(self, uri):
        results = self.connection_uri_parser.search(uri)
        if results:
            r = gerald.utilities.dburi.Connection().parse_uri(results.group('connect_string'))
            self.username = r.get('user') or self.username
            self.password = r.get('password') or self.password
            self.hostname = r.get('host') or self.hostname
            self.set_class_from_rdbms_name(results.group('rdbms'))
            self.port = self.port or self.default_port        
            return True
        else:
            return False
    def set_class_from_rdbms_name(self, rdbms_name):
        for cls in (OracleInstance, PostgresInstance, MySQLInstance):
            if cls.rdbms == rdbms_name:
                self.__class__ = cls        
    def uri(self):
        return '%s://%s:%s@%s:%s/%s' % (self.rdbms, self.username, self.password,
                                         self.hostname, self.port, self.database)  
    def determine_rdbms(self):
        if self.opts.mysql:
            self.__class__ = MySQLInstance
        elif self.opts.postgres:
            self.__class__ = PostgresInstance
        else:
            self.set_class_from_rdbms_name(self.default_rdbms)     
    def set_defaults(self):
        self.port = self.default_port
    def set_corrections(self):
        pass
    def set_instance_number(self, instance_number):
        self.instance_number = instance_number
        self.prompt = "%d:%s@%s> " % (self.instance_number, self.username, self.database)  
    sqlname = pyparsing.Word(pyparsing.alphas + '$_#%*', pyparsing.alphanums + '$_#%*')
    ls_parser = ( (pyparsing.Optional(sqlname + pyparsing.Suppress("/"), default="%")("owner") + 
                   pyparsing.Optional(sqlname + pyparsing.Suppress("/"), default="%")("type") + 
                   pyparsing.Optional(sqlname, default="%")("name") +
                   pyparsing.stringEnd ) 
                   | ( pyparsing.Optional(sqlname + pyparsing.Suppress("/"), default="%")("type") + 
                       pyparsing.Optional(sqlname + pyparsing.Suppress("."), default="%")("owner") +
                       pyparsing.Optional(sqlname, default="%")("name") ) +
                       pyparsing.stringEnd )
    def parse_identifier(self, identifier):
        """
        >>> opts = OptionTestDummy(postgres=True, password='password')        
        >>> db = DatabaseInstance('thedatabase theuser', opts)
        >>> result = db.parse_identifier('scott.pets')
        >>> result.owner
        'scott'
        >>> result.name
        'pets'
        >>> result = db.parse_identifier('scott/table/pets')
        >>> (result.owner, result.type, result.name)
        ('scott', 'table', 'pets')
        >>> result = db.parse_identifier('table/scott.pets')
        >>> (result.owner, result.type, result.name)
        ('scott', 'table', 'pets')
        >>> result = db.parse_identifier('')
        >>> (result.owner, result.type, result.name)
        ('', '', '')
        >>> result = db.parse_identifier('table/scott.*')
        >>> (str(result.owner), str(result.type), str(result.name))
        ('scott', 'table', '%')
        """
        identifier = identifier.replace('*', '%')
        result = self.ls_parser.parseString(identifier)
        return result
        
                                          
                      

parser = optparse.OptionParser()
parser.add_option('--postgres', action='store_true', help='Connect to postgreSQL: `connect --postgres [DBNAME [USERNAME]]`')
parser.add_option('--oracle', action='store_true', help='Connect to an Oracle database')
parser.add_option('--mysql', action='store_true', help='Connect to a MySQL database')
parser.add_option('-H', '--hostname', type='string',
                                    help='Machine where database is hosted')
parser.add_option('-p', '--port', type='int',
                                    help='Port to connect to')
parser.add_option('--password', type='string',
                                    help='Password')
parser.add_option('-d', '--database', type='string',
                                    help='Database name to connect to')
parser.add_option('-U', '--username', type='string',
                                    help='Database user name to connect as')

def connect(connstr):
    (options, args) = parser.parse_args(connstr)
    print options
    print args

class MySQLInstance(DatabaseInstance):
    rdbms = 'mysql'
    default_port = 3306
    def set_defaults(self):
        self.port = self.default_port       
        self.hostname = 'localhost'
        self.username = os.getenv('USER')
        self.database = os.getenv('USER')
    def connect(self):
        self.connection = MySQLdb.connect(host = self.hostname, user = self.username, 
                                passwd = self.password, db = self.database,
                                port = self.port, sql_mode = 'ANSI')        

class PostgresInstance(DatabaseInstance):
    rdbms = 'postgres'
    default_port = 5432
    def set_defaults(self):
        self.port = os.getenv('PGPORT') or self.default_port
        self.database = os.getenv('ORACLE_SID')
        self.hostname = os.getenv('PGHOST') or 'localhost'
        self.username = os.getenv('USER')
    def connect(self):
        self.connection = psycopg2.connect(host = self.hostname, user = self.username, 
                                 password = self.password, database = self.database,
                                 port = self.port)          
      
class OracleInstance(DatabaseInstance):
    rdbms = 'oracle'
    default_port = 1521
    connection_parser = re.compile('(?P<username>[^/\s@]*)(/(?P<password>[^/\s@]*))?(@((?P<hostname>[^/\s:]*)(:(?P<port>\d{1,4}))?/)?(?P<database>[^/\s:]*))?(\s+as\s+(?P<mode>sys(dba|oper)))?',
                                     re.IGNORECASE)
    def uri(self):
        if self.hostname:
            uri = '%s://%s:%s@%s:%s/%s' % (self.rdbms, self.username, self.password,
                                           self.hostname, self.port, self.database)           
        else:
            uri = '%s://%s:%s@%s' % (self.rdbms, self.username, self.password, self.database)
        if self.mode:
            uri = '%s?mode=%d' % (uri, self.mode)
        return uri
    def set_defaults(self):
        self.port = 1521
        self.database = os.getenv('ORACLE_SID')
    def set_corrections(self):
        if self.mode:
            self.mode = getattr(cx_Oracle, self.mode.upper())
        if self.hostname:
            self.dsn = cx_Oracle.makedsn(self.hostname, self.port, self.database)
        else:
            self.dsn = self.database
    def parse_connect_uri(self, uri):
        if DatabaseInstance.parse_connect_uri(self, uri):
            if not self.database:
                self.database = self.hostname
                self.hostname = None
                self.port = self.default_port
            return True            
        return False
    def connect(self):
        self.connection = cx_Oracle.connect(user = self.username, password = self.password,
                                  dsn = self.dsn, mode = self.mode)    
    def findAll(self, target):
          
        pass 
        
                 
if __name__ == '__main__':
    doctest.testmod()
