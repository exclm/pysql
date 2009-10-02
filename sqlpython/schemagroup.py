import gerald, re, datetime, threading

def get_schemagroup(rdbms, connstr, connection, user):
    gerald_connstring = connstr.split('/?mode=')[0].replace('//','/')
    if rdbms == 'oracle':
        childtype = OracleSchemaGroup            
    grp = childtype(gerald_connstring, connection, user)
    return grp
    
class RefreshThread(threading.Thread):
    def __init__(self, schemagroup, owner):
        print 'beginning a thread for ' + owner
        threading.Thread.__init__(self)
        self.schemagroup = schemagroup
        self.owner = owner
        self.schema = self.schemagroup.schemas.get(self.owner)
    def run(self):
        if self.schema and (self.schema.age() < self.schema.refreshed):
            self.schema.refreshed = self.schema.time()
        else:
            self.schema = self.schemagroup.childtype(self.owner, self.schemagroup)
        self.schemagroup.schemas[self.owner] = self.schema
        print 'finished thread for ' + self.owner
            
class SchemaGroup(object):
    def __init__(self, gerald_connstring, connection, user):
        self.connstring = gerald_connstring
        self.connection = connection
        self.cursor = connection.cursor()
        self.user = user    
    def refresh(self):
        # should trigger the beginning of a refresh
        # or maybe check whether one is needed?
        now = self.schemas[self.user].time()
        for schemaname in self.all_schemanames():
            schema_update_thread = RefreshThread(self, schemaname)
            schema_update_thread.start()
            
class OracleSchema(gerald.OracleSchema):
    def __init__(self, schemaname, parent_group):
        self.parent_group = parent_group
        gerald.OracleSchema.__init__(self, schemaname, 
                                     self.parent_group.connstring)
        self.refreshed = self.time()
    def time(self):
        curs = self.parent_group.connection.cursor()
        curs.execute('SELECT sysdate FROM dual')
        return curs.fetchone()[0]
    def age(self):
        curs = self.parent_group.connection.cursor()
        curs.execute('''SELECT max(last_ddl_time) 
                        FROM   all_objects
                        WHERE  owner = :owner''',
                        {'owner': self.name})
        return curs.fetchone()[0]            
                
class OracleSchemaGroup(SchemaGroup):         
    childtype = OracleSchema
    def __init__(self, connection_string, connection, user):
        SchemaGroup.__init__(self, connection_string, connection, user)
        self.schemas = {user: OracleSchema(user, self)}
    def all_schemanames(self):
        self.cursor.execute('SELECT DISTINCT owner FROM all_objects')
        return [r[0] for r in self.cursor.fetchall()]        
        