import re
import os
import getpass
import gerald
import time
import threading
import pickle
import optparse
import doctest

try:
    import cx_Oracle
except ImportError:
    pass

try:
    import psycopg2
except ImportError:
    pass

try:
    import MySQLdb
except ImportError:
    pass

class ObjectDescriptor(object):
    def __init__(self, name, dbobj):
        self.fullname = name
        self.dbobj = dbobj
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
                                 compiled.match(self.unqualified_name) or
                                 compiled.match(self.unqualified_path))
        
class GeraldPlaceholder(object):
    current = False
    complete = False   
    
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
    
class ConnectionData(object):
    username = None
    password = None
    hostname = None
    port = None
    database = None
    mode = 0
    connection_uri_parser = re.compile('(postgres|oracle|mysql|sqlite|mssql):/(.*$)', re.IGNORECASE)    
    connection_parser = re.compile('((?P<database>\S+)(\s+(?P<username>\S+))?)?')    
    def __init__(self, arg, opts, default_rdbms = 'oracle'):
        '''
        >>> opts = OptionTestDummy(postgres=True, password='password')        
        >>> ConnectionData('thedatabase theuser', opts).uri()        
        'postgres://theuser:password@localhost:5432/thedatabase'
        >>> opts = OptionTestDummy(password='password')
        >>> ConnectionData('oracle://user:password@db', opts).uri()        
        'oracle://user:password@db'
        >>> ConnectionData('user/password@db', opts).uri()
        'oracle://user:password@db'
        >>> ConnectionData('user/password@db as sysdba', opts).uri()
        'oracle://user:password@db?mode=2'
        >>> ConnectionData('user/password@thehost/db', opts).uri()        
        'oracle://user:password@thehost:1521/db'
        >>> opts = OptionTestDummy(postgres=True, hostname='thehost', password='password')
        >>> ConnectionData('thedatabase theuser', opts).uri()        
        'postgres://theuser:password@thehost:5432/thedatabase'
        >>> opts = OptionTestDummy(mysql=True, password='password')
        >>> ConnectionData('thedatabase theuser', opts).uri()        
        'mysql://theuser:password@localhost:3306/thedatabase'
        >>> opts = OptionTestDummy(mysql=True, password='password')
        >>> ConnectionData('thedatabase', opts).uri()        
        'mysql://catherine:password@localhost:3306/thedatabase'
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
    def parse_connect_uri(self, uri):
        results = self.connection_uri_parser.search(uri)
        if results:
            (self.username, self.password, self.hostname, self.port, self.database
             ) = gerald.utilities.dburi.Connection().parse_uri(results.group(2))
            self.set_class_from_rdbms_name(results.group(1))
            self.port = self.port or self.default_port        
            return True
        else:
            return False
    def set_class_from_rdbms_name(self, rdbms_name):
        for cls in (OracleConnectionData, PostgresConnectionData, MySQLConnectionData):
            if cls.rdbms == rdbms_name:
                self.__class__ = cls        
    def uri(self):
        return '%s://%s:%s@%s:%s/%s' % (self.rdbms, self.username, self.password,
                                         self.hostname, self.port, self.database)  
    def gerald_uri(self):
        return self.uri().split('?mode=')[0]    
    def determine_rdbms(self):
        if self.opts.mysql:
            self.__class__ = MySQLConnectionData
        elif self.opts.postgres:
            self.__class__ = PostgresConnectionData
        else:
            self.set_class_from_rdbms_name(self.default_rdbms)     
    def set_defaults(self):
        self.port = self.default_port
    def set_corrections(self):
        pass

class MySQLConnectionData(ConnectionData):
    rdbms = 'mysql'
    default_port = 3306
    def set_defaults(self):
        self.port = self.default_port       
        self.hostname = 'localhost'
        self.username = os.getenv('USER')
        self.database = os.getenv('USER')
    def connection(self):
        return MySQLdb.connect(host = self.hostname, user = self.username, 
                                passwd = self.password, db = self.database,
                                port = self.port, sql_mode = 'ANSI')        

class PostgresConnectionData(ConnectionData):
    rdbms = 'postgres'
    default_port = 5432
    def set_defaults(self):
        self.port = os.getenv('PGPORT') or self.default_port
        self.database = os.getenv('ORACLE_SID')
        self.hostname = os.getenv('PGHOST') or 'localhost'
        self.username = os.getenv('USER')
    def connection(self):
        return psycopg2.connect(host = self.hostname, user = self.username, 
                                 password = self.password, database = self.database,
                                 port = self.port)          
      
class OracleConnectionData(ConnectionData):
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
        if ConnectionData.parse_connect_uri(self, uri):
            if not self.database:
                self.database = self.hostname
                self.hostname = None
                self.port = self.default_port
            return True            
        return False
    def connection(self):
        return cx_Oracle.connect(user = self.username, password = self.password,
                                  dsn = self.dsn, mode = self.mode)    

gerald_classes = {'oracle': gerald.oracle_schema.User,
                  'postgres': gerald.PostgresSchema,
                  'mysql': gerald.MySQLSchema }

class DatabaseInstance(object):
    import_failure = None
    username = None
    password = None
    port = None
    uri = None
    pickledir = os.path.join(os.getenv('HOME'), '.sqlpython')
    connection_uri_parser = re.compile('(postgres|oracle|mysql|sqlite|mssql):/(.*$)', re.IGNORECASE)
    
    def __init__(self, arg, opts, default_rdbms = 'oracle'):
        #opts.username = opts.username or opts.user
        self.conn_data = ConnectionData(arg, opts, default_rdbms)
        for v in ('username', 'database', 'rdbms'):
            setattr(self, v, getattr(self.conn_data, v))
        self.connection = self.conn_data.connection()
        self.gerald = GeraldPlaceholder()
        self.discover_metadata()        
        
    def discover_metadata(self):
        self.metadata_discovery_thread = MetadataDiscoveryThread(self)
        self.metadata_discovery_thread.start()
           
    def set_instance_number(self, instance_number):
        self.instance_number = instance_number
        self.prompt = "%d:%s@%s> " % (self.instance_number, self.username, self.database)  
    def pickle(self):
        try:
            os.mkdir(self.pickledir)
        except OSError:
            pass 
        picklefile = open(self.picklefile(), 'w')
        pickle.dump(self.gerald.schema, picklefile)
        picklefile.close()
    def picklefile(self):
        return os.path.join(self.pickledir, ('%s.%s.%s.%s.pickle' % 
                             (self.rdbms, self.username, self.conn_data.hostname, self.database)).lower())
    def retreive_pickled_gerald(self):
        picklefile = open(self.picklefile())
        schema = pickle.load(picklefile)
        picklefile.close()
        newgerald = gerald_classes[self.rdbms](self.username, None)
        newgerald.connect(self.conn_data.gerald_uri())
        newgerald.schema = schema  
        newgerald.current = False
        newgerald.complete = True      
        newgerald.descriptions = {}        
        for (name, obj) in newgerald.schema.items():
            newgerald.descriptions[name] = ObjectDescriptor(name, obj)                    
        self.gerald = newgerald
        
class MetadataDiscoveryThread(threading.Thread):
    def __init__(self, db_instance):
        threading.Thread.__init__(self)
        self.db_instance = db_instance
    def run(self):
        if not self.db_instance.gerald.complete:
            try:
                self.db_instance.retreive_pickled_gerald()
            except IOError:
                pass
        self.db_instance.gerald.current = False
        newgerald = gerald_classes[self.db_instance.rdbms](self.db_instance.username, self.db_instance.conn_data.gerald_uri())
        newgerald.descriptions = {}
        for (name, obj) in newgerald.schema.items():
            newgerald.descriptions[name] = ObjectDescriptor(name, obj)            
        newgerald.current = True
        newgerald.complete = True
        self.db_instance.gerald = newgerald
        self.db_instance.pickle()
                 
if __name__ == '__main__':
    doctest.testmod()
