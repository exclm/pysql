import gerald, re

def schemagroup(rdbms, connstr, connection, user):
    gerald_connstring = connstr.split('/?mode=')[0].replace('//','/')
    if rdbms == 'oracle':
        childtype = OracleSchemaGroup            
    grp = childtype(gerald_connstring, connection, user)
    return grp
    
class SchemaGroup(object):
    def __init__(self, gerald_connstring, connection, user):
        self.connstring = gerald_connstring
        self.connection = connection
        self.cursor = connection.cursor()
        self.user = user    
    def refresh(self):
        now = self.schemas[self.user].time()
        for schemaname in self.all_schemanames():
            if ((schemaname not in self.schemas) or 
                (self.schemas[schemaname].age() < now) 
                ):
                self.schemas[schemaname] = self.childtype(schemaname,
                                                          self)
'SELECT owner, max(last_ddl_time) FROM all_objects GROUP BY owner'


class OracleSchema(gerald.OracleSchema):
    def __init__(self, schemaname, parent_group):
        self.parent_group = parent_group
        gerald.OracleSchema.__init__(self, schemaname, 
                                     self.parent_group.connstring)
        self.refreshed = self.time()
    def time(self):
        self.parent_group.cursor.execute('SELECT sysdate FROM dual')
        return self.parent_group.cursor.fetchone()[0]
    def age(self):
        self.parent_group.cursor.execute('''SELECT max(last_ddl_time) 
                                            FROM   all_objects
                                            WHERE  owner = :owner''',
                                            {'owner': self.name})
        return self.parent_group.cursor.fetchone()[0]            
                
class OracleSchemaGroup(SchemaGroup):         
    childtype = OracleSchema
    def __init__(self, connection_string, connection, user):
        SchemaGroup.__init__(self, connection_string, connection, user)
        self.schemas = {user: OracleSchema(user, self)}
    def all_schemanames(self):
        self.cursor.execute('SELECT DISTINCT owner FROM all_objects')
        return [r[0] for r in self.cursor.fetchall()]        
        