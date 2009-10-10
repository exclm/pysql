import gerald, re, datetime, threading, time, operator

def gerald_connection_string(sqlalchemy_connection_string):
    return sqlalchemy_connection_string.split('/?mode=')[0].replace('//','/')

def build_column_list(schema):
    schema.column_names = [[c for c in o.columns] for o in schema.schema.values() 
                           if hasattr(o, 'columns') 
                           and hasattr(o.columns, 'keys')]
    schema.column_names = reduce(operator.add, schema.column_names, [])
    schema.table_names = []
    schema.qual_table_names = []
    for t in schema.schema.values():
        if hasattr(t, 'columns') and isinstance(t.columns, dict):
            schema.table_names.append(t.name)
            schema.qual_table_names.append('%s.%s' % (schema.name, t.name))
            for c in t.columns:
                schema.column_names.append('%s.%s' % (t.name, c))
    schema.qual_column_names = ['%s.%s' % (schema.name, c) for c in schema.column_names]
        
class RefreshThread(threading.Thread):
    def __init__(self, schemagroup, owner):
        threading.Thread.__init__(self)
        self.schemagroup = schemagroup
        self.owner = owner
        self.schema = self.schemagroup.schemas.get(self.owner)
    def run(self):
        if (not self.schema) or (self.schema.is_stale()):
            self.schema = self.schemagroup.childtype(self.owner, self.schemagroup)
        else:
            self.schema.refreshed = self.schema.time()
        self.schemagroup.schemas[self.owner] = self.schema                                                
        build_column_list(self.schema)
        
class RefreshGroupThread(threading.Thread):
    def __init__(self, schemas):
        threading.Thread.__init__(self)
        self.parent = threading.current_thread()
        self.schemas = schemas
        self.daemon = True
    def run(self):
        self.schemas.refresh()
        s.column_names = reduce(operator.add, 
                                [s.qual_column_names for s in self.schemas.values()],
                                [])
        s.table_names = reduce(operator.add, 
                               [s.qual_table_names for s in self.schemas.values()],
                               [])
        
class SchemaDict(dict):
    schema_types = {'oracle': gerald.OracleSchema}
    def __init__(self, dct, rdbms, user, connection, connection_string):
        dict.__init__(self, dct)
        self.child_type = self.schema_types[rdbms]
        self.user = user
        self.connection = connection
        self.gerald_connection_string = gerald_connection_string(connection_string)
        self.refresh_thread = RefreshGroupThread(self)
        self.complete = 0
    def refresh_asynch(self):
        self.refresh_thread.start()
    def get_current_database_time(self):
        curs = self.connection.cursor()
        curs.execute('SELECT sysdate FROM dual')
        return curs.fetchone()[0]              
    def refresh(self):
        current_database_time = self.get_current_database_time()
        curs = self.connection.cursor()
        curs.execute('''SELECT   owner, MAX(last_ddl_time)
                        FROM     all_objects
                        GROUP BY owner
                        -- sort :username to top
                        ORDER BY REPLACE(owner, :username, 'A'), owner''',
                     {'username': self.user.upper()})
        for (owner, last_ddl_time) in curs.fetchall():
            if (owner not in self) or (self[owner].refreshed < last_ddl_time):
                self.refresh_one(owner, current_database_time)
                # what if a user's last object is deleted?
            if isinstance(self.complete, int):
                self.complete += 1
        self.column_names = [s.column_names for s in self.values()]
        self.columns = reduce(operator.add, [s.column_names for s in self.values()])
        self.complete = 'all'
        print 'metadata discovered'
    def refresh_one(self, owner, current_database_time=None):
        if not current_database_time:
            current_database_time = self.get_current_database_time()
        self[owner] = self.child_type(owner, self.gerald_connection_string)
        self[owner].refreshed = current_database_time        
        build_column_list(self[owner])

class PlainObject(object):
    '''Simply a dumb container for attributes.'''
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def transform(self, transformation):
        '''Attempts to apply a transformation function to all the 
           user-defined attributes; fails silently on errors'''
        for (k, v) in self.__dict__.items():
            try:
                self.__dict__[k] = transformation(v)
            except:
                pass
        return self
    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, 
                           ','.join('%s=%s' % (k, 
                                               (isinstance(v, basestring) and "'%s'" % v) or v)
                           for (k, v) in sorted(self.__dict__.items())))

    
class MetaData(PlainObject):
    def __init__(self, object_name, schema_name, db_object):
        self.object_name = object_name
        self.schema_name = schema_name
        self.db_object = db_object
        if isinstance(db_object, dict):
            self.db_type = db_object['db_type']
        elif hasattr(db_object, 'type'):
            self.db_type = db_object.type
        else:   
            self.db_type = str(type(db_object)).rstrip("'>").split('.')[-1]
    def qualified_name(self):
        return '%s.%s' % (self.schema_name, self.object_name)
    def name(self, qualified=False):
        if qualified:
            return self.qualified_name()
        else:
            return self.object_name   
    def descriptor(self, qualified=False):
        return '%s/%s' % (self.db_type, self.name(qualified))
        
s = None

if __name__ == '__main__':
    connection_string = 'oracle://jrrt:password@orcl/?mode=0'
    connection = None
    dct = {}
    user = 'jrrt'
    rdbms = 'oracle'
    s = SchemaDict(dct, rdbms, user, connection, connection_string, 100)
    sch = s.child_type('jrrt',s.gerald_connection_string)
    