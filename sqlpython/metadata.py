from collections import defaultdict

metaqueries = defaultdict(defaultdict)

metaqueries['desc']['oracle'] = defaultdict(defaultdict)
metaqueries['desc']['oracle']['TABLE']['long'] = """
SELECT atc.column_id "#",
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
ORDER BY atc.column_id;"""

metaqueries['desc']['oracle']['TABLE']['short'] = """
SELECT atc.column_name,
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
ORDER BY atc.column_id;"""

metaqueries['desc']['oracle']['PROCEDURE'] = """
SELECT NVL(argument_name, 'Return Value') argument_name,             
data_type,
in_out,
default_value
FROM all_arguments
WHERE object_name = :object_name
AND      owner = :owner
AND      package_name IS NULL
ORDER BY sequence;"""

metaqueries['desc']['oracle']['PackageObjects'] = """
SELECT DISTINCT object_name
FROM all_arguments
WHERE package_name = :package_name
AND      owner = :owner"""

metaqueries['desc']['oracle']['PackageObjArgs'] = """
SELECT object_name,
argument_name,             
data_type,
in_out,
default_value
FROM all_arguments
WHERE package_name = :package_name
AND      object_name = :object_name
AND      owner = :owner
AND      argument_name IS NOT NULL
ORDER BY sequence;"""
