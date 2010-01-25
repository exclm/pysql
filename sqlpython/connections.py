import re
import os
import gerald
import schemagroup

class Connection(object):
    password = None
    uri = None
    connection_uri_parser = re.compile('(postgres|oracle|mysql|sqlite|mssql):/(.*$)', re.IGNORECASE)
    
    def __init__(self, arg, opts, default_rdbms = 'oracle'):
        self.default_rdbms = default_rdbms
        if not self.parse_connect_uri(arg):
            self.parse_connect_arg(arg, opts)
        self.reconnect()
        self.discover_schemas()
    
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
        self.password = opts.password    
        self.host = opts.hostname
        self.oracle_connect_mode = 0
        if opts.postgres:
            self.__class__ = PostgresConnection
        elif opts.mysql:
            self.__class__ = MySQLConnection
        elif opts.oracle:
            self.__class__ = OracleConnection
        else:
            self.__class__ = rdbms_types.get(self.default_rdbms)
        self.assign_args(arg, opts)
        self.db_name = opts.database or self.db_name
        self.port = self.port or self.default_port        
        self.uri = self.uri or '%s://%s:%s@%s:%s/%s' % (self.rdbms, self.username, self.password,
                                                         self.host, self.port, self.db_name)
    
    def gerald_uri(self):
        return self.uri.split('?mode=')[0]
        
    def reconnect(self):
        self.password = self.password or getpass.getpass('Password: ')
        self.connection = self.new_connection()

    def discover_schemas(self):
        self.schemas = schemagroup.SchemaDict(
            {}, rdbms = self.rdbms, user = self.username, 
            connection = self.connection, connection_string = self.gerald_uri())
        self.schemas.refresh_asynch()
    
    def set_connection_number(self, connection_number):
        self.connection_number = connection_number
        self.prompt = "%d:%s@%s> " % (self.connection_number, self.username, self.db_name)        

class OpenSourceConnection(Connection):
    def assign_args(self, opts, arg):
        self.assign_args(opts, arg)        
        self.username = username or os.environ['USER']
        self.db_name = self.db_name or self.username
        self.host = opts.host or self.host or 'localhost'

try:
    import psycopg2
    class PostgresConnection(OpenSourceConnection):
        rdbms = 'postgres'
        default_port = 5432
        def assign_details(self, arg, opts):
            self.port = os.getenv('PGPORT') or self.port
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
    class PostgresConnection(OpenSourceConnection):
        pass
            
try:
    import MySQLdb
    class MySQLConnection(OpenSourceConnection):
        rdbms = 'mysql'
        default_port = 3306        
        def assign_details(self, arg, opts):
            self.db_name = arg
        def new_connection(self):
            return MySQLdb.connect(host = self.host, user = self.username, 
                                    passwd = self.password, db = self.db_name,
                                    port = self.port, sql_mode = 'ANSI')
except ImportError:
    class MySQLConnection(OpenSourceConnection):
        pass

try:
    import cx_Oracle
    
    class OracleConnection(Connection):
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
    class OracleConnection(Connection):
        pass
                                       
rdbms_types = {'oracle': OracleConnection, 'mysql': MySQLConnection, 'postgres': PostgresConnection}
                  
        