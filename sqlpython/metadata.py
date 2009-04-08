from collections import defaultdict

metaqueries = defaultdict(defaultdict)

metaqueries['desc']['oracle'] = defaultdict(defaultdict)
metaqueries['desc']['oracle']['TABLE']['long'] = (
"""SELECT atc.column_id "#",
atc.column_name,
CASE atc.nullable WHEN 'Y' THEN 'NULL' ELSE 'NOT NULL' END "Null?",
atc.data_type ||
CASE atc.data_type WHEN 'DATE' THEN ''
ELSE '(' ||
CASE atc.data_type WHEN 'NUMBER' THEN TO_CHAR(atc.data_precision) ||
CASE atc.data_scale WHEN 0 THEN ''
ELSE ',' || TO_CHAR(atc.data_scale) END
ELSE TO_CHAR(atc.data_length) END 
END ||
CASE atc.data_type WHEN 'DATE' THEN '' ELSE ')' END
data_type,
acc.comments
FROM all_tab_columns atc
JOIN all_col_comments acc ON (acc.owner = atc.owner AND acc.table_name = atc.table_name AND acc.column_name = atc.column_name)
WHERE atc.table_name = :object_name
AND      atc.owner = :owner
ORDER BY atc.column_id;""",)

metaqueries['desc']['oracle']['TABLE']['short'] = (
"""SELECT atc.column_name,
CASE atc.nullable WHEN 'Y' THEN 'NULL' ELSE 'NOT NULL' END "Null?",
atc.data_type ||
CASE atc.data_type WHEN 'DATE' THEN ''
ELSE '(' ||
CASE atc.data_type WHEN 'NUMBER' THEN TO_CHAR(atc.data_precision) ||
CASE atc.data_scale WHEN 0 THEN ''
ELSE ',' || TO_CHAR(atc.data_scale) END
ELSE TO_CHAR(atc.data_length) END 
END ||
CASE atc.data_type WHEN 'DATE' THEN '' ELSE ')' END
data_type
FROM all_tab_columns atc
WHERE atc.table_name = :object_name
AND      atc.owner = :owner
ORDER BY atc.column_id;""",)

metaqueries['desc']['oracle']['PROCEDURE'] = (
"""SELECT NVL(argument_name, 'Return Value') argument_name,             
data_type,
in_out,
default_value
FROM all_arguments
WHERE object_name = :object_name
AND      owner = :owner
AND      package_name IS NULL
ORDER BY sequence;""",)

metaqueries['desc']['oracle']['PackageObjects'] = (
"""SELECT DISTINCT object_name
FROM all_arguments
WHERE package_name = :package_name
AND      owner = :owner""",)

metaqueries['desc']['oracle']['PackageObjArgs'] = (
"""SELECT object_name,
argument_name,             
data_type,
in_out,
default_value
FROM all_arguments
WHERE package_name = :package_name
AND      object_name = :object_name
AND      owner = :owner
AND      argument_name IS NOT NULL
ORDER BY sequence;""",)

metaqueries['desc']['oracle']['TRIGGER'] = (
"""SELECT description
FROM   all_triggers
WHERE  owner = :owner
AND    trigger_name = :object_name;
""",
"""SELECT table_owner,
base_object_type,
table_name,
column_name,
when_clause,
status,
action_type,
crossedition
FROM   all_triggers
WHERE  owner = :owner
AND    trigger_name = :object_name
\\t""",)


metaqueries['desc']['oracle']['INDEX'] = (
"""SELECT index_type,
table_owner,
table_name,
table_type,
uniqueness,
compression,
partitioned,
temporary,
generated,
secondary,
dropped,
visibility
FROM   all_indexes
WHERE  owner = :owner
AND    index_name = :object_name\\t""",)

metaqueries['desc']['oracle']['VIEW'] = metaqueries['desc']['oracle']['TABLE']['short']
metaqueries['desc']['oracle']['FUNCTION'] = metaqueries['desc']['oracle']['PROCEDURE']

metaqueries['ls']['oracle'] = """
SELECT owner, 
       object_name,  
       object_type,
       status,
       last_ddl_time,
       user as my_own
FROM   all_objects"""

metaqueries['ls']['information_schema'] = """
SELECT table_schema as owner,
       table_name as object_name,
       table_type as object_type,
       null as status,
       null as last_ddl_time,
       %(my_own)s as my_own
FROM   information_schema.tables
UNION ALL
SELECT trigger_schema as owner,
       trigger_name as object_name,
       'TRIGGER' as object_type,
       null as status,
       created as last_ddl_time,
       %(my_own)s as my_own
FROM   information_schema.triggers
UNION ALL
SELECT routine_schema as owner,
       routine_name as object_name,
       routine_type as object_type,
       null as status,
       last_altered as last_ddl_time,
       %(my_own)s as my_own
FROM   information_schema.routines
"""

metaqueries['ls']['postgres'] = (metaqueries['ls']['information_schema'] + """UNION ALL
SELECT sequence_schema as owner,
       sequence_name as object_name,
       'SEQUENCE' as object_type,
       null as status,
       null as last_ddl_time,
       %(my_own)s as my_own
FROM   information_schema.sequences""") % {'my_own': "text('public')"}
metaqueries['ls']['mysql'] = metaqueries['ls']['information_schema'] % {'my_own':"database()"}

metaqueries['ls']['sqlite'] = """
SELECT '' as owner,
       tbl_name as object_name,
       type as object_type,
       null as status,
       null as last_ddl_time,
       '' as current_username
FROM   sqlite_master"""
