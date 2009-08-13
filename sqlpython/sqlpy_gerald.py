import gerald

class SchemaSet(object):
    def __init__(self, connection, rdbms, connect_string):
        self.schemas = {}
        curs = connection.cursor()
        if rdbms == 'postgres':
            curs.execute('SELECT schema_name FROM information_schema.schemata')
            for row in curs.fetchall():
                schema = row[0]
                self.schemas[schema] = gerald.PostgresSchema(schema, connect_string)
        elif rdbms == 'oracle':
            curs.execute('SELECT DISTINCT owner FROM all_objects')
            for row in curs.fetchall():
                schema = row[0]
                
                
                
import psycopg2
connstr = 'postgres:/catherine:catherine@localhost/catherine'
conn = psycopg2.connect("dbname='catherine' user='catherine' password='catherine' host='localhost'")
ss = SchemaSet(conn, 'postgres', connstr)
