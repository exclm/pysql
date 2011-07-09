import re
import os
import getpass
import gerald
import gerald.utilities
import gerald.utilities.dburi
import time
import optparse
import doctest
import pyparsing
import dbapiext

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

if not gerald_classes:
    raise ImportError, 'No Python database adapters installed!'

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
       
class DBOjbect(object):
    def __init__(self, schema, object_type, name):
        self.schema = schema
        self.type = object_type
        self.name = name
        
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
    def object_name_case(self, name):
        return name.lower()
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
        self.determine_rdbms()  # may be altered later as connect string is parsed
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
        self.connect()
    def parse_connect_uri(self, uri):
        results = self.connection_uri_parser.search(uri)
        if results:
            self.set_class_from_rdbms_name(results.group('rdbms'))     
            r = gerald.utilities.dburi.Connection().parse_uri(results.group('connect_string'))
            self.username = r.get('user') or self.username
            self.password = r.get('password') or self.password
            self.hostname = r.get('host') or self.hostname
            self.port = self.port or self.default_port
            self.database = r.get('db_name')
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
        if self.opts.mysql or self.arg.startswith('mysql://'):
            self.__class__ = MySQLInstance
        elif self.opts.postgres or self.arg.startswith('postgres://') or self.arg.startswith('postgresql://'):
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
    typname = pyparsing.Word(pyparsing.alphas + ' ')
    ls_parser = ( (pyparsing.Optional(sqlname("owner") + "/") + 
                   pyparsing.Optional(typname("type") + "/") +
                   pyparsing.Optional(sqlname("name")) +
                   pyparsing.stringEnd ) 
                   | ( pyparsing.Optional(typname("type") + "/") +
                       pyparsing.Optional(sqlname("owner") + ".") +
                       pyparsing.Optional(sqlname("name")) +
                       pyparsing.stringEnd ))
    def parse_identifier(self, identifier):
        """
        >>> opts = OptionTestDummy(postgres=True, password='password')        
        >>> db = DatabaseInstance('thedatabase theuser', opts)
        >>> result = db.parse_identifier('scott.pets')
        >>> (result.owner, result.type, result.name)
        ('scott', '%', 'pets')
        >>> result = db.parse_identifier('pets')
        >>> (result.owner, result.type, result.name)
        ('%', '%', 'pets')
        >>> result = db.parse_identifier('pe*')
        >>> (result.owner, result.type, result.name)
        ('%', '%', 'pe%')
        >>> result = db.parse_identifier('scott/table/pets')
        >>> (result.owner, result.type, result.name)
        ('scott', 'table', 'pets')
        >>> result = db.parse_identifier('table/scott.pets')
        >>> (result.owner, result.type, result.name)
        ('scott', 'table', 'pets')
        >>> result = db.parse_identifier('')
        >>> (result.owner, result.type, result.name)
        ('%', '%', '%')
        >>> result = db.parse_identifier('table/scott.*')
        >>> (str(result.owner), str(result.type), str(result.name))
        ('scott', 'table', '%')
        """
        identifier = self.sql_format_wildcards(identifier)
        result = {'owner': '%', 'type': '%', 'name': '%'}
        result.update(dict(self.ls_parser.parseString(identifier)))
        return result 
    def comparison_operator(self, target):
        if ('%' in target) or ('_' in target):
            operator = 'LIKE'
        else:
            operator = '='
        return operator
    def sql_format_wildcards(self, target):
        return target.replace('*', '%').replace('?', '_')
    def set_operators(self, selectors):
        for selector in selectors.keys():
            if '_' in selectors[selector] or '%' in selectors[selector]:
                selectors[selector + '_op'] = 'LIKE'
            else:
                selectors[selector + '_op'] = '='
    def default_owner(self):
        return self.username
    def objects(self, target, opts):
        identifier = self.parse_identifier(target)
        if (identifier['owner'] == '%') and (not opts.all):
            identifier['owner'] = self.default_owner()
        self.set_operators(identifier)
        if hasattr(opts, 'reverse') and opts.reverse:
            identifier['sort_direction'] = 'DESC'
        else:
            identifier['sort_direction'] = 'ASC'
        curs = self.connection.cursor()
        dbapiext.execute_f(curs, self.all_object_qry, paramstyle=self.paramstyle, **identifier)
        return curs
    def columns(self, target, table_name, opts):
        target = self.sql_format_wildcards(target)
        table_name = self.sql_format_wildcards(table_name)
        identifier = {'column_name': target, 'table_name': table_name}
        if opts.all:
            identifier['owner'] = '%'
        else:
            identifier['owner'] = self.username
        self.set_operators(identifier)
        curs = self.connection.cursor()
        dbapiext.execute_f(curs, self.column_qry, paramstyle=self.paramstyle, **identifier)
        return curs
    def tables_and_views(self, target):
        identifier = {'table_name': target + '%'}
        curs = self.connection.cursor()
        dbapiext.execute_f(curs, self.tables_and_views_qry, paramstyle=self.paramstyle, **identifier)
        return curs
    def _source(self, target, opts):
        identifier = {'text': '%%%s%%' % target.lower()}
        if opts.all:
            identifier['owner'] = '%'
        else:
            identifier['owner'] = self.username
        self.set_operators(identifier)
        curs = self.connection.cursor()
        dbapiext.execute_f(curs, self.source_qry, paramstyle=self.paramstyle, **identifier)
        return curs
    def source(self, target, opts):
        curs = self._source(target, opts)
        target = re.compile(target.replace('%','.*').replace('_','.'))
        for row in curs:
            code = row[4]
            for (line_number, line) in enumerate(code.splitlines()):
                if target.search(line):
                    yield (row[0], row[1], row[2], line_number, line)
    def object_metadata(self, owner, object_type, name):
        return self.gerald_types[object_type](name, self.connection.cursor(), owner)
    tables_and_views_qry = """SELECT table_name
                              FROM   information_schema.tables
                              WHERE  table_name LIKE LOWER(%(table_name)S)"""
                      

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
    paramstyle = 'format'
    def set_defaults(self):
        self.port = self.default_port       
        self.hostname = 'localhost'
        self.username = os.getenv('USER')
        self.database = os.getenv('USER')
    def connect(self):
        self.connection = MySQLdb.connect(host = self.hostname, user = self.username, 
                                passwd = self.password, db = self.database,
                                port = self.port, sql_mode = 'ANSI')        
    def bindSyntax(self, varname):
        return '%s'
    def bindVariables(self, binds):
        'Puts a tuple of (name, value) pairs into the bind format desired by MySQL'
        return (i[1] for i in binds)
    def default_owner(self):
        return self.database
    column_qry = """SELECT c.table_schema, t.table_type, c.table_name, c.column_name
                    FROM   information_schema.columns c
                    JOIN   information_schema.tables t ON (c.table_schema = t.table_schema
                                                           AND c.table_name = t.table_name)
                    WHERE  ( (c.table_schema %(owner_op)s LOWER(%(owner)S)) OR (c.table_schema = 'public'))
                    AND    c.table_name %(table_name_op)s LOWER(%(table_name)S)
                    AND    LOWER(c.column_name) %(column_name_op)s LOWER(%(column_name)S)"""
    source_qry = """SELECT r.routine_schema, r.routine_type, r.routine_name, 0 AS line, r.routine_definition
                    FROM   information_schema.routines r
                    WHERE  r.routine_schema %(owner_op)s LOWER(%(owner)S)
                    AND    LOWER(r.routine_definition) LIKE %(text)S"""
    all_object_qry = """SELECT table_schema, table_type, table_name
                        FROM   information_schema.tables
                        WHERE  table_schema %(owner_op)s LOWER(%(owner)S)
                        AND    table_type %(type_op)s UPPER(%(type)S)
                        AND    table_name %(name_op)s %(name)S
                        ORDER BY table_schema, table_type, table_name %(sort_direction)s"""
    parameter_qry = """SHOW variables LIKE '%%%s%%'%s%s""" 
    gerald_types = {'TABLE': gerald.mysql_schema.Table,
                    'VIEW': gerald.mysql_schema.View,
                    'BASE TABLE': gerald.mysql_schema.Table,
                    #  'SYSTEM VIEW': gerald.mysql_schema.Table - system views throw errors
                    }

   
class PostgresInstance(DatabaseInstance):
    rdbms = 'postgres'
    default_port = 5432
    case = str.lower
    paramstyle = 'format'
    def set_defaults(self):
        self.port = os.getenv('PGPORT') or self.default_port
        self.database = os.getenv('PGDATABASE')
        self.hostname = os.getenv('PGHOST') or os.getenv('PGHOSTADDR') or 'localhost'
        self.username = os.getenv('PGUSER') or os.getenv('USER')
        self.password = os.getenv('PGPASSWORD')
    def connect(self):
        self.connection = psycopg2.connect(host = self.hostname, user = self.username, 
                                 password = self.password, database = self.database,
                                 port = self.port)          
    def bindSyntax(self, varname):
        return '%%(%s)s' % varname
    def bindVariables(self, binds):
        'Puts a tuple of (name, value) pairs into the bind format desired by psycopg2'
        return dict((b[0], b[1].lower()) for b in binds)
    all_object_qry = """SELECT table_schema, table_type, table_name
                        FROM   information_schema.tables
                        WHERE  ( (table_schema %(owner_op)s LOWER(%(owner)S)) OR (table_schema = 'public') )
                        AND    table_type %(type_op)s UPPER(%(type)S)
                        AND    table_name %(name_op)s LOWER(%(name)S)
                        ORDER BY table_schema, table_type, table_name %(sort_direction)s"""
    column_qry = """SELECT c.table_schema, t.table_type, c.table_name, c.column_name      
                    FROM   information_schema.columns c
                    JOIN   information_schema.tables t ON (c.table_schema = t.table_schema
                                                           AND c.table_name = t.table_name)
                    WHERE  ( (c.table_schema %(owner_op)s LOWER(%(owner)S)) OR (c.table_schema = 'public'))
                    AND    c.table_name %(table_name_op)s LOWER(%(table_name)S)
                    AND    c.column_name %(column_name_op)s LOWER(%(column_name)S)"""
    source_qry = """SELECT r.routine_schema, r.routine_type, r.routine_name, 0 AS line, r.routine_definition
                    FROM   information_schema.routines r
                    WHERE  ( (r.routine_schema %(owner_op)s LOWER(%(owner)S)) OR (r.routine_schema = 'public') )
                    AND    LOWER(r.routine_definition) LIKE %(text)S"""
    parameter_qry = """SELECT name, unit, setting FROM pg_settings WHERE name LIKE LOWER('%%%s%%')%s%s""" 
    gerald_types = {'BASE TABLE': gerald.postgres_schema.Table,
                    'VIEW': gerald.postgres_schema.View}

class OracleInstance(DatabaseInstance):
    rdbms = 'oracle'
    default_port = 1521
    paramstyle = 'named'
    connection_parser = re.compile('(?P<username>[^/\s@]*)(/(?P<password>[^/\s@]*))?(@((?P<hostname>[^/\s:]*)(:(?P<port>\d{1,4}))?/)?(?P<database>[^/\s:]*))?(\s+as\s+(?P<mode>sys(dba|oper)))?',
                                     re.IGNORECASE)
    def object_name_case(self, name):
        return name.upper()
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
    all_object_qry = """SELECT owner, object_type, object_name 
                        FROM   all_objects 
                        WHERE  owner %(owner_op)s UPPER(%(owner)S)
                        AND    object_type %(type_op)s UPPER(%(type)S)
                        AND    object_name %(name_op)s UPPER(%(name)S)
                        ORDER BY owner, object_type, object_name %(sort_direction)s"""
    column_qry = """SELECT atc.owner, ao.object_type, atc.table_name, atc.column_name      
                    FROM   all_tab_columns atc
                    JOIN   all_objects ao ON (atc.table_name = ao.object_name AND atc.owner = ao.owner)
                    WHERE  atc.owner %(owner_op)s UPPER(%(owner)S)
                    AND    atc.table_name %(table_name_op)s UPPER(%(table_name)S)
                    AND    atc.column_name %(column_name_op)s UPPER(%(column_name)S) """
    source_qry = """SELECT owner, type, name, line, text
                    FROM   all_source
                    WHERE  owner %(owner_op)s %(owner)S
                    AND    lower(text) LIKE %(text)S"""
    tables_and_views_qry = """SELECT table_name
                              FROM   all_tables
                              WHERE  table_name LIKE UPPER(%(table_name)S)"""
    parameter_qry = """SELECT name, 
                                              CASE type WHEN 1 THEN 'BOOLEAN'
                                                        WHEN 2 THEN 'STRING'
                                                        WHEN 3 THEN 'INTEGER'
                                                        WHEN 4 THEN 'PARAMETER FILE'
                                                        WHEN 5 THEN 'RESERVED'
                                                        WHEN 6 THEN 'BIG INTEGER' END type, 
                                                        value 
                                       FROM v$parameter 
                                       WHERE name LIKE LOWER('%%%s%%')%s%s"""
    def source(self, target, opts):
        return self._source(target, opts)
    def bindSyntax(self, varname):
        return ':' + varname
    def bindVariables(self, binds):
        'Puts a tuple of (name, value) pairs into the bind format desired by cx_Oracle'
        return dict((b[0], b[1].upper()) for b in binds)
    gerald_types = {'TABLE': gerald.oracle_schema.Table,
                    'VIEW': gerald.oracle_schema.View}

                
if __name__ == '__main__':
    opts = OptionTestDummy(password='password')
    db = DatabaseInstance('oracle://system:twttatl@orcl', opts)
    print list(db.findAll(''))
    #doctest.testmod()
