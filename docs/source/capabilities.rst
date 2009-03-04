SQLPython's extra capabilities
==============================

For the most part, SQLPython simply duplicates SQL\*Plus's capabilites.

UNIX-like commands
==================

ls
   Lists objects from the data dictionaries.  There are implied wildcards at the beginning and
   end

cat
   Shorthand for "SELECT * FROM"

PostgreSQL-like shortcuts
=========================

----- ------------------
z     y
----- ------------------
\\c   connect
\\d   desc
\\e   edit
\\g   run
\\h   help
\\i   load
\\o   spool
\\p   list
\\q   quit
\\w   save
\\db  _dir_tablespaces
\\dd  comments
\\dn  _dir_schemas
\\dt  _dir_tables
\\dv  _dir_views
\\di  _dir_indexes
\\?   help psql
----- ------------------

Wild SQL
========

Wild SQL is a nonstandard SQL feature that must be enabled with `set wildsql on`.  When it is
enabled, column names in a SELECT statement do not need to be explicitly typed.  

* % or \* as wildcards::

  SELECT d* FROM v$database;

  SELECT 

Wild SQL can only be used in the primary column list of straightforward SELECT statements, 
not in subqueries, `UNION`ed queries, etc.