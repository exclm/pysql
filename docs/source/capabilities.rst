SQLPython's extra capabilities
==============================

For the most part, SQLPython simply duplicates SQL\*Plus's capabilites.

Neatened output
===============

When printing query results, sqlpython economizes on screen space by allocating
only the width each column actually needs.

Smart prompt
============

sqlpython automatically uses `username`@`instance`> as its prompt, helping
avoid wrong-instance and wrong-user errors.

Tab completion
==============

When typing SQL commands, hitting `<TAB>` after entering part of an object
or column name brings up a list of appropriate possibilities or, if there
is only one possibility, fills in the rest of the name.  This feature is
not yet very reliable, but can save typing.

Scripting
=========

Like SQL\*Plus, sqlpython can run scripts (text files with series of SQL and
sqlpython commands) with `@/path/to/script.sql` or (for online scripts)
`@http://scripthost/scriptlibrary/script.sql`.

History
=======

The up- and down-arrow keys allow you to scroll through the lines entered so far
in your sqlpython session.

Commands are also entered into a command history.

  `history` or `hi`
    List entire command history

  `list` or `li`
    List only last command

  `hi <N>`
    List command number <N> from history.  

  `hi <N>-`, `hi -<N>`
    List commands from <N> onward, or up to <N>

  `hi <str>`
    Lists commands that include the string <str>

  `hi /<regex>/` 
    Lists commands that match the regular expression <regex>

  `run`, `r`, or `\\g`
    Run the most recent command again

  `run <N>`
    Run command <N>

  `run <str>`, `run /<regex>/`
    Run command matching <str> or <regex> (as for `history`) - 
    if multiple items would match, run most recent

UNIX-like commands
==================

Many sqlpython commands allow you to act as though the database objects
were files in a UNIX filesystem.  Many of the commands also accept flags
to modify their behavior.

ls
   Lists objects from the data dictionaries, as though they were in a 
   *object_type*/*object_name* directory structure.  Thus, `ls view/`
   lists all the user's views.

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
