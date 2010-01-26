import re
import os
import getpass
import gerald
import schemagroup
import time
import threading

class ObjectDescriptor(object):
    def __init__(self, name, dbobj):
        self.fullname = name
        self.dbobj = dbobj
        self.type = str(type(self.dbobj)).split()[-1].lower()
        self.path = '%s/%s' % (self.type, self.fullname)
        #self.type_path = '%s/' % self.dbobj.type
        (self.owner, self.unqualified_name) = self.fullname.split('.')
        self.owner = self.owner.lower()
    def match_pattern(self, pattern, specific_owner=None):
        return ( pattern.match(fullname) or 
                  pattern.match(self.type) or 
                  ((not specific_owner) and pattern.match(self.unqualified_name)) or
                  ((self.owner == specific_owner.lower()) and pattern.match(self.unqualified_name)) )
        
class GeraldPlaceholder(object):
    current = False
    complete = False
    
class DatabaseInstance(object):
    password = None
    uri = None
    connection_uri_parser = re.compile('(postgres|oracle|mysql|sqlite|mssql):/(.*$)', re.IGNORECASE)
    
    def __init__(self, arg, opts, default_rdbms = 'oracle'):
        self.default_rdbms = default_rdbms
        if not self.parse_connect_uri(arg):
            self.parse_connect_arg(arg, opts)
        self.connection = self.new_connection()
        self.gerald = GeraldPlaceholder()
        self.metadata_discovery_thread = MetadataDiscoveryThread(self)
        self.metadata_discovery_thread.start()
    
    def parse_connect_uri(self, uri):
        results = self.connection_uri_parser.search(uri)
        if results:
            (self.username, self.password, self.host, self.port, self.db_name
             ) = gerald.utilities.dburi.Connection().parse_uri(results.group(2))
            self.__class__ = rdbms_types.get(results.group(1))
            self.uri = uri
            self.port = self.port or self.default_port        
            return True
        else:
            return False
            
    def parse_connect_arg(self, arg, opts):
        self.host = opts.hostname
        self.oracle_connect_mode = 0
        if opts.postgres:
            self.__class__ = PostgresDatabaseInstance
        elif opts.mysql:
            self.__class__ = MySQLDatabaseInstance
        elif opts.oracle:
            self.__class__ = OracleDatabaseInstance
        else:
            self.__class__ = rdbms_types.get(self.default_rdbms)
        self.assign_args(arg, opts)
        self.db_name = opts.database or self.db_name
        self.port = self.port or self.default_port        
        self.password = self.password or opts.password or getpass.getpass('Password: ')        
        self.uri = self.uri or '%s://%s:%s@%s:%s/%s' % (self.rdbms, self.username, self.password,
                                                         self.host, self.port, self.db_name)
    
    def gerald_uri(self):
        return self.uri.split('?mode=')[0]
        
    def discover_schemas(self):
        self.gerald = self.gerald_class(self.username, self.gerald_uri())
        self.gerald.descriptions = {}
        for (name, obj) in self.gerald.schema.items():
            self.gerald.descriptions[name] = ObjectDescriptor(name, obj)            
        self.gerald.current = True
        self.gerald.complete = True
    
    def set_instance_number(self, instance_number):
        self.instance_number = instance_number
        self.prompt = "%d:%s@%s> " % (self.instance_number, self.username, self.db_name)        

class OpenSourceDatabaseInstance(DatabaseInstance):
    def assign_args(self, arg, opts):
        self.assign_details(arg, opts)        
        self.username = self.username or os.environ['USER']
        self.db_name = self.db_name or self.username
        self.host = opts.hostname or self.host or 'localhost'

try:
    import psycopg2
    class PostgresDatabaseInstance(OpenSourceDatabaseInstance):
        gerald_class = gerald.PostgresSchema
        rdbms = 'postgres'
        default_port = 5432
        def assign_details(self, arg, opts):
            self.port = opts.port or os.getenv('PGPORT') or self.default_port
            self.host = self.host or os.getenv('PGHOST')
            args = arg.split()
            if len(args) > 1:
                self.username = args[1]
            if len(args) > 0:
                self.db_name = args[0]   
        def new_connection(self):
            return psycopg2.connect(host = self.host, user = self.username, 
                                     password = self.password, database = self.db_name,
                                     port = self.port)                
except ImportError:
    class PostgresDatabaseInstance(OpenSourceDatabaseInstance):
        pass
            
try:
    import MySQLdb
    class MySQLDatabaseInstance(OpenSourceDatabaseInstance):
        gerald_class = gerald.MySQLSchema
        rdbms = 'mysql'
        default_port = 3306        
        def assign_details(self, arg, opts):
            self.db_name = arg
        def new_connection(self):
            return MySQLdb.connect(host = self.host, user = self.username, 
                                    passwd = self.password, db = self.db_name,
                                    port = self.port, sql_mode = 'ANSI')
except ImportError:
    class MySQLDatabaseInstance(OpenSourceDatabaseInstance):
        pass

try:
    import cx_Oracle
    
    class OracleDatabaseInstance(DatabaseInstance):
        gerald_class = gerald.oracle_schema.User
        rdbms = 'oracle'
        connection_parser = re.compile('(?P<username>[^/\s]*)(/(?P<password>[^/\s]*))?@((?P<host>[^/\s:]*)(:(?P<port>\d{1,4}))?/)?(?P<db_name>[^/\s:]*)(\s+as\s+(?P<mode>sys(dba|oper)))?',
                                            re.IGNORECASE)
        connection_modes = {'SYSDBA': cx_Oracle.SYSDBA, 'SYSOPER': cx_Oracle.SYSOPER}
        oracle_connect_mode = 0
        default_port = 1521
        def assign_args(self, arg, opts):
            connectargs = self.connection_parser.search(arg)
            self.username = connectargs.group('username')
            self.password = connectargs.group('password')
            self.db_name = connectargs.group('db_name')
            self.port = connectargs.group('port') or self.default_port
            self.host = connectargs.group('host')
            if self.host:
                self.dsn = cx_Oracle.makedsn(self.host, self.port, self.db_name)
            else:
                self.dsn = self.db_name
                self.uri = '%s://%s:%s@%s' % (self.rdbms, self.username, self.password, self.db_name)
            if connectargs.group('mode'):
                self.oracle_connect_mode = self.connection_modes.get(connectargs.group('mode').upper())
        def new_connection(self):
            return cx_Oracle.connect(user = self.username, 
                                      password = self.password,
                                      dsn = self.dsn,
                                      mode = self.oracle_connect_mode)
            
                                           
except ImportError:
    class OracleDatabaseInstance(DatabaseInstance):
        pass
        
class MetadataDiscoveryThread(threading.Thread):
    def __init__(self, db_instance):
        threading.Thread.__init__(self)
        self.db_instance = db_instance
    def run(self):
        self.db_instance.gerald = self.db_instance.gerald_class(self.db_instance.username, self.db_instance.gerald_uri())
        self.db_instance.gerald.descriptions = {}
        for (name, obj) in self.db_instance.gerald.schema.items():
            self.db_instance.gerald.descriptions[name] = ObjectDescriptor(name, obj)            
        self.db_instance.gerald.current = True
        self.db_instance.gerald.complete = True

rdbms_types = {'oracle': OracleDatabaseInstance, 'mysql': MySQLDatabaseInstance, 'postgres': PostgresDatabaseInstance}
                  
        