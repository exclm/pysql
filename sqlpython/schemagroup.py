import gerald, re, datetime, threading, time

def gerald_connection_string(sqlalchemy_connection_string):
    return sqlalchemy_connection_string.split('/?mode=')[0].replace('//','/')
    
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
            
class RefreshGroupThread(threading.Thread):
    def __init__(self, schemas, minutes_between_refreshes):
        threading.Thread.__init__(self)
        self.parent = threading.current_thread()
        self.schemas = schemas
        self.minutes_between_refreshes = minutes_between_refreshes
        self.daemon = True
    def run(self):
        while self.parent.isAlive():
            self.schemas.refresh()
            time.sleep(60 * self.minutes_between_refreshes)
        
class SchemaDict(dict):
    schema_types = {'oracle': gerald.OracleSchema}
    def __init__(self, dct, rdbms, user, connection, connection_string, minutes_between_refreshes):
        dict.__init__(self, dct)
        self.child_type = self.schema_types[rdbms]
        self.user = user
        self.connection = connection
        self.gerald_connection_string = gerald_connection_string(connection_string)
        self.refresh_thread = RefreshGroupThread(self, minutes_between_refreshes)
        self.complete = False
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
        self.complete = True
    def refresh_one(self, owner, current_database_time=None):
        if not current_database_time:
            current_database_time = self.get_current_database_time()
        self[owner] = self.child_type(owner, self.gerald_connection_string)
        self[owner].refreshed = current_database_time        
        