==============================
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

Special I/O destinations
========================

Much as in a UNIX shell, you can follow a command with a special output destination.

`> {filename}` sends the output to a file.  This is more convenient than SQL\*Plus's 
SPOOL {filename}... SPOOL OFF (though you can use those as well).

`>` alone (no filename) sends the output to the paste buffer.

`|` pipes the output to an operating-system command.

When `< {filename}` is included in your command, it is replaced with the contents of
{filename} before the command is run.

Examples:: 

Special output formats
======================

By replacing the `;` that terminates a SELECT statement with a backslash-character
sequence, you can get output in a number of useful formats.  The `terminators`
command lists them, for your convenience::

===  ======================== ================================
                              Especially useful for
===  ======================== ================================
;    standard Oracle format
\c   CSV (with headings)      sending to spreadsheets   
\C   CSV (no headings)
\g   list                     wide output with linewraps
\G   aligned list
\h   HTML table               web reports
\i   INSERT statements        copying to other instances
\j   JSON
\s   CSV (with headings)
\S   CSV (no headings)
\t   transposed               "narrow" tables like v$database
\x   XML
\l   line plot, with markers
\L   scatter plot (no lines)
\b   bar graph
\p   pie chart
===  ======================== ================================

Most of these output formats are even more useful when combined with special output
destinations.  For example, `SELECT * FROM party\h > /var/www/party_report.html`
could create an HTML report in the webserver's documents directory, ready to serve.

UNIX-like commands
==================

Many sqlpython commands allow you to act as though the database objects
were files in a UNIX filesystem.  Many of the commands also accept flags
to modify their behavior.

ls {object type/object name, with wildcards}
  Lists objects from the data dictionaries, as though they were in a 
  *object_type*/*object_name* directory structure.  Thus, `ls view/\*`
  lists all the user's views.  Calling with no argument is equivalent
  to `ls *`.
   
  Options::
  
    -l, --long      long descriptions 
    -a, --all       all schemas' objects (otherwise, you only get your own)
    -t, --timesort  Sort by last_ddl_time
    -r, --reverse   Reverse order while sorting   

  `ls -lt *;10` lists the ten items with the most recent last_ddl_time;
  this can be a good way to answer the question, "What was I working on?"
  
cat {remainder of query}
   Shorthand for "SELECT * FROM".  Can be combined with anything else
   that fits into a SELECT statement (WHERE, ORDER BY, etc.)
   
grep {grep {target} {table} [{table2,...}]
   Equivalent to SELECT * FROM {table} WHERE *any column* LIKE '%{target}%'
   Useful when you don't know, don't remember, or don't care which column
   a value may be found in.
   
  Options::
  
    -i, --ignore-case  Case-insensitive search   

find -c {target}, find -t {column}
  Lists all tables or columns whose names contain {target}.  More convenient than
  querying user_tab_columns/all_tab_columns or user_tables/all_tables.
  Options::
    -a           Find all objects (not just my own)  
  
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

PL/SQL source code
==================

pull {object_name}
  Displays the PL/SQL source code for {object_name}.
  
  Options:
    -d, --dump   dump results to files (object_type/object_name.sql)
    -f, --full   get dependent objects as well
    -a, --all    all schemas' objects
  
bzr, git, hg {object_name}
  Dump source code to files, as `pull -f`, but also creates or commits to a
  repository of the appropriate distributed version control system
  (Bazaar, Git, or Mercurial, respectively).  
  
find {target}
  Lists all PL/SQL objects whose source code contains the {target} string.  
  Always case-insensitive.
  Options::
    -a           Search all PL/SQL objects (not just my own)    
  

Bind variables
==============

Bind variables work in sqlpython as they do in SQL\*Plus, but they are set dynamically; there
is no need to declare them before use.  The syntax for setting them is more permissive than
in SQL\*Plus; all these are recognized::

  exec :mybind := 'value'
  exec :mybind = 'value'
  :mybind := 'value'
  :mybind = 'value'

The current values of all bind variables can be viewed with the `print` command.

The `bind` command creates and populates bind variables for the final row of the most recent
SELECT statement executed; each column name is used as a bind variable, which is filled with
the value.  `bind -r {rownumber}` does the same, but fills from row {rownumber} instead of
from the final row (row numbers begin at 0 for this command).

When the `autobind` sqlpython parameter is True, a `bind` statement is issued automatically
after every query that returns exactly one row.

Bind variables are available from within Python as a dictionary named `binds` (see Python).

Substitution variables
======================

Substitution variables ("&" variables) work much as they do in SQL\*Plus.  As in SQL\*Plus,
the `scan` parameter determines whether queries are scanned to replace substitution 
variables.  Unlike SQL\*Plus, sqlpython knows how annoying it is to hit a substitution
variable you didn't expect, so entering "SET SCAN OFF" when prompted for a substitution
variable actually aborts the substitution process.

Wild SQL
========

Wild SQL is a nonstandard SQL feature that must be enabled with `set wildsql on`.  When it is
enabled, column names in a SELECT statement do not need to be explicitly typed; they can be
specified with special Wild SQL symbols: wildcards (`*`, `%`, `_`); column numbers (`#{N}`);
and NOT-style exclusion (`!`).  The symbols can even be combined.

::

  jrrt@orcl> cat party
  
  NAME    STR INT WIS DEX CON CHA
  ------- --- --- --- --- --- ---
  Frodo     8  14  16  15  14  16
  Gimli    17  12  10  11  17  11
  Legolas  13  15  14  18  15  17
  Sam      11   9  14  11  16  13
  
  4 rows selected.
  
  jrrt@orcl> set wild on
  wildsql - was: False
  now: True
  jrrt@orcl> select *i* from party;
  
  INT WIS
  --- ---
   14  16
   12  10
   15  14
    9  14
  
  4 rows selected.
  
  jrrt@orcl> select #1, #5 from party;
  
  NAME    DEX
  ------- ---
  Frodo    15
  Gimli    11
  Legolas  18
  Sam      11
  
  4 rows selected.
  
  jrrt@orcl> select !str from party;
  
  NAME    INT WIS DEX CON CHA
  ------- --- --- --- --- ---
  Frodo    14  16  15  14  16
  Gimli    12  10  11  17  11
  Legolas  15  14  18  15  17
  Sam       9  14  11  16  13
  
  4 rows selected.
  
  jrrt@orcl> select n*, !#3, !c* from party;
  
  NAME    STR WIS DEX
  ------- --- --- ---
  Frodo     8  16  15
  Gimli    17  10  11
  Legolas  13  14  18
  Sam      11  14  11
  
  4 rows selected.

Wild SQL symbols only work in the first SELECT statement in a query; they do not work in 
subqueries, subsequent UNIONed queries, etc.

Python
======

The `py` command allows the user to execute Python commands, either one-at-a-time (with
`py {command}`) or in an interactive environment (beginning with a bare `py` statement,
and continuing until `end py` is entered).

A history of result sets from each query is exposed to the python session as the list `r`; 
the most recent result set is `r[-1]`. Bind variables are exposed as the dictionary `binds`. 
All variables are retained each time the python environment is entered (whether interactively, 
or with one-line `py` statements).

Resultsets in `r` are read-only, but `binds` can be written as well as read, and will 
be working bind variables in the SQL environment.

::

  0:testschema@eqtest> select title, author from play;
  
  TITLE           AUTHOR
  --------------- -----------
  Timon of Athens Shakespeare
  Twelfth Night   Shakespeare
  The Tempest     Shakespeare
  Agamemnon       Aeschylus
  
  4 rows selected.
  
  0:testschema@eqtest> py import urllib
  0:testschema@eqtest> py current_season = urllib.urlopen('http://cincyshakes.com/').read()
  0:testschema@eqtest> py
  Now accepting python commands; end with `end py`
  >>> r[-1]
  [('Timon of Athens', 'Shakespeare'), ('Twelfth Night', 'Shakespeare'), ('The Tempest', 'Shakespeare'), ('Agamemnon', 'Aeschylus')]
  >>> for row in r[-1]:
  ...     print '%s by %s' % (row.title, row.author)
  Timon of Athens by Shakespeare
  Twelfth Night by Shakespeare
  The Tempest by Shakespeare
  Agamemnon by Aeschylus
  >>> [row.title for row in r[-1] if row.title in current_season]
  ['Timon of Athens', 'Twelfth Night']
  >>> binds['nowplaying'] = [row.title for row in r[-1] if row.title in current_season][0]
  >>> end py
  0:testschema@eqtest> print
  :nowplaying = Timon of Athens
  0:testschema@eqtest> select title, author from play where title = :nowplaying;
  
  TITLE           AUTHOR
  --------------- -----------
  Timon of Athens Shakespeare
  
  1 row selected.

Parameters
==========

Several parameters control the behavior of sqlpython itself.  

===================== ==================================================  ===============
                                                                          default
===================== ==================================================  ===============
autobind              When True, single-row queries automatically `bind`  False
commit_on_exit        Automatically commits work at end of session        True
continuation_prompt   Prompt for second line and onward of long statement >
default_file_name     The file opened by `edit`, if not specified         afiedt.buf
echo                  Echo command entered before executing               False
editor                Text editor invoked by `edit`.                      varies
heading               Print column names                                  True
maxfetch              Maximum number of rows to return from any query     1000
maxtselctrows         Maximum # of rows from a tselect or \\n query       10
prompt                Probably unwise to change                           user@instance>
scan                  Interpret & as indicating substitution variables    True
serveroutput          Print DBMS_OUTPUT.PUT_LINE results                  True
sql_echo              Print text of "behind-the-scenes" queries           False
timeout               In seconds                                          30
timing                Print time for each command to execute              False
wildsql               Accept *, %, #, and ! in column names               False
===================== ==================================================  ===============

The user can change these with the `set {paramname} {new-value}` statement.  
The True/False parameters accept new
values permissively, recognizing "True", "False", "T", "F", "yes", "no", "on", "off"...

`set` and `show` both list the current values of the sqlpython parameters.
`show parameter {param}` shows current Oracle parameters (from v$parameter), as it does
in SQL\*Plus.

Tuning
======

In sqlpython, `explain {SQL ID}` shows the execution plan for the SQL statement with the
given ID.  If SQL ID is omitted, it defaults to the most recent SQL executed.
(This is not necessarily the last statement `EXPLAIN PLAN` was issued against.)

Other specialized sqlpython tuning commands include:

load
  Displays OS load on cluster nodes (10gRAC)
  
longops
  Displays long-running operations

sessinfo
  Reports session info for the given sid, extended to RAC with gv$  
  
top, top9i
  Displays active sessions


  
  

