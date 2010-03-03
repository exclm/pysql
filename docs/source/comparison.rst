This paper is a comparative guide to sqlpython and
three other open-source SQL\*Plus alternatives (gqlplus, Senora, YASQL).

******************************************************
Long Live the Command Line: SQL\*Plus and Alternatives
******************************************************

`COLLABORATE 09 <http://www.ioug.org/collaborate09/>`_

Talk #405 - Database track

Thursday, May 7, 2009, 11:00 AM - 12:00 PM

Orange County Convention Center West

Orlando, FL

============
Introduction
============

Common desktop productivity applications, like spreadsheets, word processors, and the Microsoft Access database, make no clear separation between the program's handling of its underlying data and the interface it provides for user access.  Coming from this world, newcomers to relational databases like Oracle are often confused by the distinction between the database itself and the variety of programs that may be used to access it.  For my first several months of working with Oracle, "Oracle" and "SQL\*Plus" were basically synonyms in my mind.

In reality, there is a great variety of options for accessing data.  End users generally use tools that channel their interaction and insulate them from SQL - tools like Oracle Forms, Reports, and Discoverer; homegrown GUI applications; and web-based interfaces, sometimes built on platforms like Oracle Application Express.

Database administrators and developers need more general-purpose tools that let them see and manipulate data and metadata freely and issue ad-hoc SQL statements, exercising any DML and DDL privileges their accounts have been granted.  GUI tools have gained much attention since the introduction of Oracle SQL Developer, though Quest Software's TOAD remains extremely popular due to its rich feature set and vigorous development.  Other GUI tools include PL/SQL Developer, TORA, and open-source tools like Squirrel.  Oracle Enterprise Manager and 
JDeveloper can also be used for ad-hoc access to Oracle tables and data.

Nonetheless, command-line interaction through SQL\*Plus remains a cornerstone of most Oracle professionals' work.  SQL\*Plus is ubiquitous and familiar, running on virtually any system.  
Typing a familiar SQL or SQL\*Plus command is often faster than navigating a GUI's menus.
SQL\*Plus gives experienced users a sense of full control of their system.  Finally, professionals trying to avoid repetitive motion injuries may find frequent use of a mouse uncomfortable, preferring the ergonomics of a good keyboard.

SQL\*Plus still appears much the same as it did years ago, and it's easy to assume that command-line clients are inherently limited, bare-bones approaches.  There have been improvements, however, which many users are unaware of; by educating yourself about SQL\*Plus' newer features, you may find that SQL\*Plus is a more powerful tool than you'd realized. 

Furthermore, SQL\*Plus is not the only command-line client for interacting with Oracle.  Over the years, Oracle professionals craving greater capabilities have produced several alternate command-line clients that introduce extra features they found useful, and you may as well.  In fact, since all these tools are open-source, you are welcome to add new features to meet your own needs, and to contribute your improvements for incorporation into the tools.  All the SQL\*Plus alternative tools are free of charge.  (SQL\*Plus is also available free of charge, since it is packaged with free Oracle products like the Oracle XE client.)

This paper will begin with a short introduction to each of the tools reviewed.  It will then present enhanced capabilities, most of which appear in more than one of the tools.  Next, it will list the most SQL\*Plus capabilities that some or all of the alternative products lack.  Next, it will cover installing and extending each tool, and finally, briefly discuss cross-RDBMS SQL client tools.

For purposes of this paper, "UNIX" implies UNIX, Linux, and similar POSIX-based operating 
systems - essentially anything but Windows.  Curly braces (`{}`) denote non-literal values,
as in `{username}/{password}`.

=====
Tools
=====

SQL\*Plus
---------

Oracle's command-line SQL interface, and possibly the most familiar face of Oracle to the world.  We will take the well-known features of SQL\*Plus as our baseline, assuming that readers are familiar with them.  Some of its lesser-known features, however, will be included in our review of enhanced features.

gqlplus
-------

This tool is essentially a thin wrapper around SQL\*Plus, passing all input 
directly to SQL\*Plus.  It preserves virtually all SQL\*Plus' capabilities 
and feel.  Gqlplus was written in C by Ljubomir J. Buturovic and available under the GNU General 
Public License.  Version 1.12 was released in December 2006.  It
is available from its SourceForge page at http://gqlplus.sourceforge.net/.

senora
------

Senora - an acronym for Shell ENvironment for ORAcle - is a Perl-based tool was created by 
Martin Drautzburg in 2003.  As its name suggests, its focus is on adding features of the UNIX shell to a SQL\*Plus-like environment.  Version 0.5.1 was released under the
Artistic License in April 2003.  A few of the capabilities
described here apply only to the 0.6 release, planned for early 2009; they are labelled as such in the text.
Senora is available from its SourceForge page at http://senora.sourceforge.net/.

Senora uses a plugin architecture; some of its commands are not available
in any given senora session until the plugin is activated with the `register` command.  For example, senora's
tuning-related commands will not be available until `register Tuning` is executed in the session.  
A startup file, `login.sra`, can be used to automatically register all desired plugins on startup.

YASQL
-----

Another Perl program, this one by Nathan Shafer and Balint Kozman.  Many of its advanced features center around producing query output in more versatile and convenient forms.  Version 1.83 was released under the GNU General Public License in May 2005.  It is available from its SourceForge page at http://sourceforge.net/projects/yasql/.

sqlpython
---------

A Python program by Luca Canali and Catherine Devlin (this author).  It imitates the features of senora and YASQL as well as introducing many unique features.  Active development is ongoing, and version 1.6.1 
was released in March 2009.  Some defects as of this paper's writing (March 2009) are likely to be fixed by the time you read it.  It is available from the Python Package Index at http://pypi.python.org/pypi/sqlpython

====================
Windows Availability
====================

========= ===
gqlplus   no
senora    yes 
YASQL     no
sqlpython yes
========= ===

Since gqlplus and YASQL were written in C and Perl, respectively, it should be possible,
in principle, to compile and run them on Windows.  No precompiled versions of them are
available, however, and no Windows installation procedures have been documented.

All the tools are available for all UNIX environments.

============
Enhancements
============

Smart prompt
------------

*SQL\*Plus (10g and higer), senora, YASQL, sqlpython*

`SQL>`, the standard SQL\*Plus prompt, provides no useful information.  The prompt can be changed with SQL\*Plus' `SET SQLPROMPT` command.

As any DBA who has mistakenly issued a command in what they *believed* was the development instance can tell you, the most useful prompt is one that identifies what username and database is
being used, like `me@production>`.  To get this prompt in SQL\*Plus, issue `SET SQLPROMPT "_user'@'_connect_identifier> "`.

It's important that the prompt be kept up-to-date; if a `CONNECT` statement is used to connect to a different instance, the prompt must be updated or it will become deceptive.  In SQL\*Plus, `SET SQLPROMPT` should be included in `$ORACLE_HOME/sqlplus/admin/glogin.sql`.  SQL\*Plus 10g and higher execute the commands in `glogin.sql` each time a CONNECT statement changes this information.

SQL\*Plus 9i and earlier run `glogin.sql` only when a new session is started, as does gqlpython.  In these environments, the "smart prompt" cannot be trusted, since a `CONNECT` statement may have changed the reality.

Senora, YASQL, and sqlpython provide this type of smart prompt out of the box.

Tab completion
--------------

*gqlplus, YASQL, sqlpython*

Tab completion saves typing and avoids spelling errors by filling in the 
remainder of a command or object name when 
the first few letters are entered and the TAB key is hit.  If there are multiple valid
endings to an incomplete word, each potential ending.

Editor choice
-------------

*all*

It's important to remember to set the `$EDITOR` environment variable before starting any
command-line tool under UNIX.  All the tools allow textfile editing, but if $EDITOR is 
not set, they will use the system default editor - generally UNIX `ed`, which can be traumatizing.

sqlpython does not give up so easily if `$EDITOR` is not set, searching for more advanced
text editors and starting them preferentially.

Scripting
---------

*all*

All the tools support running scripts with `@path/to/script.sql`.  Establishing a personal 
library of script files is an important part of building your productivity.  SQL\*Plus,
gqlplus, and sqlpython also support running scripts from urls, like 
`@http://host.com/scriptlibrary/myscript.sql`, allowing you to keep your script library
on the web.

The convenience of the script library is crucial.  If your scripts are hidden away in
a directory that is difficult to remember and type, you will be tempted to rewrite
queries instead of using your established scripts.  It's good practice to always start
your SQL tool in the directory that contains your script library; that way, you can
access your scripts without having to type path names.  An alias or shortcut at the 
operating-system level can be useful; for instance, put `alias sql='cd ~/myscriptlibrary; sqlplus'` in your `.bashrc` file.

Choose your script names carefully, so that you will find them easily in the future.  
To view your script library from within your SQL tool, type `host dir` or `host ls`.

Command history
---------------

*SQL\*Plus (Windows, or with rlwrap), gqlplus, senora, YASQL, sqlpython*

On Windows, the up- and down-arrow keys can be used to scroll through 
the history of SQL\*Plus commands issued during the session.  SQL\*Plus on UNIX does not provide this feature.  You can restore the feature, however, by installing a free GNU tool called `rlwrap`, then invoking SQL*\Plus under it: `rlwrap sqlplus me@instance`.
`rlwrap` can also provide cursor-key history to senora, and in fact to any command-line program. 

Gqlplus and sqlpytyhon provide cursor-key command history out of the box; Senora and YASQL do also, provided
that the Term::ReadLine::Perl module has been installed (see Installation).

In addition, senora and sqlpython have a `history` or `hi` command that gives a numbered list of all commands issued in the session.  

Senora history commands
~~~~~~~~~~~~~~~~~~~~~~~

================== ===============================================
hi                 List all commands issued in this session  
hi {search string} List all commands containing {search string}
!                  rerun the last command
!!{N}              rerun command number N
!{search string}   rerun last command containing {search string}
================== ===============================================

sqlpython history commands
~~~~~~~~~~~~~~~~~~~~~~~~~~

========================= ==========================================================
hi                        List all commands issued in this session
hi {N}                    List command number {N}
hi -{N}                   List all commands up to command number {N}
hi {N}-                   List all commands from command number {N} onward
hi {search string}        List all commands containing {search string}   
hi /{regex}/              List all commands matching regular expression /{regex}/
r or \\g                  rerun the last command
r {N}                     rerun command number {N}
r {search string}         rerun last command containing {search string}
r /{regex}/               rerun last command matching {regex}
========================= ==========================================================
  
Neatened output
---------------

*senora, YASQL, sqlpython*

Senora, YASL, and sqlpython economize on column space when returning query results.  This
can make output much neater, more compact, and easier to read.  

SQL\*Plus::

  SQL> select * from party where name = 'Gimli';
  
  NAME						STR	   INT	      WIS	 DEX	    CON        CHA
  ---------------------------------------- ---------- ---------- ---------- ---------- ---------- ----------
  Gimli						 17	    12	       10	  11	     17 	11

YASQL::

  jrrt@orcl> select * from party where name = 'Gimli';


  NAME   STR  INT  WIS  DEX  CON  CHA
  ----- ---- ---- ---- ---- ---- ----
  Gimli   17   12   10   11   17   11

  1 row selected (0.03 seconds)

UNIX-inspired commands  
----------------------

*senora, sqlpython*

"Senora" is an acronym for Shell ENvironment for ORAcle, and many of its special features 
are inspired directly by UNIX shell commands.  `sqlpython` duplicates most of these.  Also, as
in Unix, these commands can be altered with flags.

ls
  `ls` is used to list Oracle objects from the data dictionary.  These are reported as though
  they existed in an {object type}/{object name} directory structure::

    0:jrrt@orcl> ls
    Table/Party                             Index/Xpk_Party                         
    
    0:jrrt@orcl> ls -h
    NAME
      ls - list all objects matching pattern
    
    SYNOPSIS
      ls <type/name>
      -a             List all objects, even with a dollar
      -l             List validity of objects too
      -C             List constraints etc too
      -I             List indexes etc too
      -i             List invalid objects only
    
    FILES
      DataDictionary.pm
    0:jrrt@orcl> ls -l Table/*
    VALID   27-FEB-09               Table/Party


cat
  A shortcut for `SELECT * FROM`.  In fact, you can
  attach `WHERE` clauses, `ORDER BY`, or other SQL just as if you had typed `SELECT * FROM`.

head [-n N] 
  Displays the first N rows (default 10) of a table or view.
  
grep *target_text* *table to search* [*table 2 to search*, ...]
  Searches entire tables (all columns) for the desired text::
  
      0:jrrt@orcl> grep 17 party
      
      Name   |str|int|wis|dex|con|cha|
      --------------------------------
      Gimli  | 17| 12| 10| 11| 17| 11|
      Legolas| 13| 15| 14| 18| 15| 17|
      
      2 rows selected.
      
Also like UNIX commands, the operation of many senora and sqlpython commands can be altered by
using flags, as in `grep -i {target text} {table name}` , where `-i` makes the search case-insensitive.
See `{command} -h` for help on each command, including a list of flags.

Data dictionary access
----------------------

*senora, YASQL, sqlpython*

Inspecting Oracle objects using the data dictionary requires plenty of typing and an 
excellent memory.  The alternative tools provide convenient shortcuts.

This table shows some approximately equivalent ways to extract object 
information from the data dictionary; actually, the SQL queries
given require considerable interpretation and usually additional joins to get truly
useful information, whereas the YASQL/senora/sqlpython commands provide information
ready-to-use.  There are too many possibilities to list, but a sample will give the idea.

+------------------------+-----------------+-----------------+----------------------+ 
|SQL\*Plus               |YASQL            |senora           |sqlpython             |
+========================+=================+=================+======================+
|SELECT table_name       |show tables      |ls Table/\*      |ls table              |
|FROM   tabs;            |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+ 
|SELECT object_name,     |                 |                 |ls -l \*a\*           |
|status, last_ddl_time   |                 |                 |                      |
|FROM   all_objects      |                 |                 |                      |
|WHERE  object_name      |                 |                 |                      |
|LIKE 'A%';              |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+
|SELECT *                |show constraints |refs {table name}|refs {table name}     |
|FROM   all_constraints  |on {table name}  |                 |                      |
|WHERE  table_name =     |                 |                 |                      |
|'{table name}'          |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+
|SELECT *                |show indexes     |                 |\\di {table name}     |
|FROM   user_indexes     |on {table name}  |                 |                      |
|WHERE  table_name =     |                 |                 |                      |
|'{table name}'          |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+
|SELECT *                | show triggers   |                 |                      |
|FROM   all_triggers     | on {table name} |                 |                      |
|WHERE  table_name =     |                 |                 |                      |
|'{table name}'          |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+
|DBMS_METADATA.GET_DDL(  |                 |pull             |pull                  |
|'{object_type}',        |                 |{object_name}    |{object_name}         |
|'{object_name}')        |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+
|SELECT * FROM           |                 |desc -l          | comments {table name}|
|all_tab_comments        |                 |{table_name}     | or \\dd {table name} |
|WHERE table_name =      |                 |(available in    |                      |
|'{table name}';         |                 |v0.6)            |                      |
|SELECT * FROM           |                 |                 |                      |
|all_col_comments        |                 |                 |                      |
|WHERE table_name =      |                 |                 |                      |
|'{table name}';         |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+
|SELECT *                |                 |find {target}    | find -a {target}     |
|FROM   all_source       |                 |                 |                      |
|WHERE  text LIKE        |                 |                 |                      |
|'%{target}%';           |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+ 
|SELECT *                |                 |                 |find -ac {column name}|
|FROM all_tab_columns    |                 |                 |                      |
|WHERE column_name LIKE  |                 |                 |                      |
|'%{column name}%'       |                 |                 |                      |
+------------------------+-----------------+-----------------+----------------------+ 

In sqlpython, the command `ls -tl;10` will list the most recent ten objects by their 
last DDL time - which can be a handy way to answer the question, "What was I working
on here?"  (`ls -tl` is similarly useful in the Unix shell.)

convenient viewing of explain plans
-----------------------------------

*senora, YASQL, sqlpython*

In senora, `xplain {text of query to explain}` is the equivalent of issuing 
`EXPLAIN PLAN FOR {query}` in SQL\*Plus, then querying the PLAN table with
spacing inserted for neat formatting.

In YASQL, `show plan` displays the last PLAN table entry, neatly formatted.
(Issuing `EXPLAIN PLAN` first is up to you.)

In sqlpython, `explain {SQL ID}` shows the execution plan for the SQL statement with the
given ID.  If SQL ID is omitted, it defaults to the most recent SQL executed.
(This is not necessarily the last statement `EXPLAIN PLAN` was issued against.)

Special I/O destinations
------------------------

*YASQL, sqlpython*

You can use the UNIX pipe (`|`) to send query output to a UNIX shell command; this will work much like the pipe in the UNIX shell would.  An example in sqlpython::

  jrrt@orcl> select name from party; | sed 's/Legolas/Elfie-poo/'
  
  4 rows selected.
  
  NAME   
  -------
  Frodo  
  Gimli  
  Elfie-poo
  Sam    

You can use `> {filename}` to route output into a file.

In sqlpython, if the filename is omitted after a `>`, the output is simply redirected into the
paste buffer, and can then be pasted into a document, email, etc.  An external program called
`xclip` is necessary to make this work under Unix, and can be installed from your package
repository.

In YASQL, `<` can be used to import data directly from a CSV file into a table::

  jrrt@orcl> insert into party values (:1, :2, :3, :4, :5, :6, :7); < newmembers.csv

In sqlpython, `< {filename}` simply replaces `< {filename}` with the content of {filename},
then executes the resulting command.

Special output formats
----------------------

*SQL\*Plus, YASQL, sqlpython*

SQL\*Plus can produce HTML tables instead of plain text using the `SET MARKUP ON` command.
Using this, a query could be published as a webpage entirely from within a SQL\*Plus
session::

  > set markup html on
  > spool /var/www/myreport.html
  > select * from mytable;
  > spool off
  > set markup html off

YASQL and sqlpython have much more extensive, and convenient, output formatting options.
By simply replacing the ";" terminating a query with a special backslash sequence, you can
get output in a variety of alternate formats.

=== ===================================
\\b bar graph (sqlpython)
\\c CSV (sqlpython)
\\c CSV (no column names) (sqlpython)
\\G list (aligned)
\\g list (not aligned)
\\h HTML table (sqlpython)
\\i as SQL `insert` statements
\\j JSON (sqlpython)
\\l line plot, with markers (sqlpython)
\\l line plot, no markers (sqlpython)
\\p pie chart (sqlpython)
\\s CSV
\\S CSV (no column names)
\\t transposed (sqlpython)
\\x XML (sqlpython)
=== ===================================

Thus, the sqlpython way to produce and web-publish a report fits on a single line::

  > select * from party\h > /var/www/party.html

List (`\\g`) output can be especially useful in reading tables with many columns without confusing
line wrapping.  Transposed (`\\t`) output is ideal for reading many-columns/few-rows tables
like V$DATABASE.  Generating plots directly from queries is just fun.

Row output limits
-----------------

*YASQL, sqlpython*

Follow the terminator in a query (usually ";") with a positive integer, and the query will only
output up to that number of rows::

  jrrt@orcl> select * from party;2

  NAME  STR INT WIS DEX CON CHA
  ----- --- --- --- --- --- ---
  Frodo   8  14  16  15  14  16
  Gimli  17  12  10  11  17  11

  2 rows selected.

Multiple sessions
-----------------

*senora, sqlpython*

When `connect -a {username@instance}` is used to create a new connection, senora does not close the
old connection.  It keeps both connections alive, and switching between them is far more convenient
than creating new connections::

  Enter sample here

psql-like shortcuts
-------------------

*YASQL, sqlpython*

Several backslash-character command shortcuts have been copied from psql, the command-line tool
for the PostgreSQL open-source database, into YASQL and sqlpython.

==== =====================================
\\c  connect (sqlpython)
\\c  clear buffer (YASQL)
\\d  describe (sqlpython)
\\e  edit
\\g  run (sqlpython)
\\h  help (sqlpython)
\\i  load (sqlpython)
\\l  list (YASQL)
\\o  spool (sqlpython)
\\p  list
\\q  quit
\\w  save
\\db directory of tablespaces (sqlpython)
\\dd comments (sqlpython)
\\dn directory of schemas (sqlpython)
\\dt directory of tables
\\dv directory of views
\\di directory of indexes
==== =====================================

Enhanced bind variables
-----------------------

*sqlpython*

Senora and sqlpython support SQL\*Plus-style bind variables.  sqlpython also has an optional, easygoing
syntax for defining bind variables and permits them to be dynamically defined (no declaration required)::

  jrrt@orcl> :name = 'Legolas'
  jrrt@orcl> print
  :name = Legolas

sqlpython's `bind` command creates and populates bind variables for each
column of the row most recently returned from a query.  The optional `autobind` 
setting automatically does this after every query that returns a single row.

::

  jrrt@orcl> select name, str, int from party where name = :name;

  NAME    STR INT
  ------- --- ---
  Legolas  13  15

  1 row selected.

  jrrt@orcl> print
  :1 = Legolas
  :2 = 13
  :3 = 15
  :int = 15
  :name = Legolas
  :str = 13

Tuning
------

*senora, sqlpython*

Each program provides an assortment of commands to provide performance-related data.  
There are too many commands for detailed description, but a partial list will supply
some idea for the capabilities.  

Senora tuning commands
~~~~~~~~~~~~~~~~~~~~~~

============== ====== ==========================================================
command        abbrev effect
============== ====== ==========================================================
analyzeObject  ana    analyze tables or indexes
cacheStats     cst    Display memory statisticts
compareStat    coms   compare statistics of two schemas
cstatement     cs     lists current SQL statements, by session
cstatement -S  cs -S  lists current SQL statements with their execution stats
FkeyIndexes    fki    analyze the existance of foreign key indexes
hwm                   get high watermark info on analyzed tables (experimental)
jobs                  print job information
kept                  show kept (pinned) code
kill                  kill a session
locks                 show sessions and the objects the are waiting for
logs                  print redo log activity
profile               estimate current execution times
ps                    print session information
resize                resize datafiles 
rollSegs              print rollback info
show parameter sp     show init.ora parameter
space                 show tablespace and file stats
stat                  print session statistics
validate       vi     xvalidate structure an index
waits                 show what sessions are waiting for
xqueries       xq     show most expensive quieries
============== ====== ==========================================================

Before senora tuning commands can be run, `register Tuning` must be executed in the session.

sqlython tuning commands
~~~~~~~~~~~~~~~~~~~~~~~~

======== =====================================================
load     prints the OS load on all cluster nodes (10g RAC)
longops  prints from gv$session_longops
sessinfo prints session information. Parameter: sid
sql      prints the sql text from the cache. Parameter: sql_id
top      List top active sessions
top9i    9i (and single instance) version of top
======== =====================================================

Wildcards in column names
-------------------------

*YASQL, sqlpython*

YASQL supports `\*` wildcards in column names, if there is a ~/.yasqlrc or /etc/yasql.conf file containing
`column_wildcards=1`.

sqlpython's wildcards are more powerful.  When the option wildsql is set to ON, 
sqlpython will accept these in the column list of a SELECT statement:

  * Wildcards (`\*` or `%`, and `?`)

  * Column numbers (`#1, #2`)

  * !, meaning NOT.  `!str` means "all columns except STR".

These can be combined.  `SELECT !#2, !c% FROM party` means 'select all columns except column #2 and any column beginning with 'C'", and is translated by sqlpython into `SELECT name, int, wis, dex FROM party;`.

====================
Drawbacks and quirks
====================

No tool reproduces all the features of SQL\*Plus (though gqlplus comes very, very close).  These are the drawbacks most likely to be noticed.

Smart prompt
------------

Like SQL\*Plus, gqlplus invokes glogin.sql when it is started.  Unfortunately, gqlplus does not re-invoke it when a new CONNECT statement is issued during a session.  Thus, as for SQL\*Plus versions xxxx and before, the "smart prompt" can become dangerously deceptive in gqlplus.

PL/SQL
------

Gqlplus, Senora, and sqlpython can run all PL/SQL as SQL\*Plus does.  

YASQL can run single lines of PL/SQL with `exec`, and automatically echoes DBMS_OUTPUT.PUT_LINE output, but it does not recognize anonymous SQL BEGIN..END blocks.  sqlpython requires that PL/SQL blocks be bracketed
in `REMARK BEGIN` and `REMARK END` statements

Executing shell commands
------------------------

In SQL\*Plus, `host {command}` or `!{command}` run {command} on the operating system.
These work in all the alternative tools as well, except that senora recognizes only 
`host` (since, in senora, `!` is used for re-running commands from the history instead.)

Error messages
--------------

Error messages in some programs are less friendly than in SQL*\Plus.  For instance, senora
responds to most errors with "what ?"::

  0:jrrt@orcl> grep;
  what ? "grep;" ?
  
sqlpython passes Python or Oracle errors it encounters up to the user, but it cannot
highlight the place in a SQL command where a syntax error took place.

When compiling PL/SQL objects (functions, packages, procedures) that contain errors, 
the tools vary in the quality of information they return.
 
* Senora reports that a compilation error has occured, and `show errors` works as expected.
      
* YASQL reports that a compilation error has occured.  `show errors` in YASQL lists the compilation errors for *all* invalid PL/SQL objects in the schema.
  
* sqlpython reports errors immediately upon compilation.
      
Note that, in senora and YASQL, abbreviated forms of `show errors`, like `sho err`, are not recognized.

Startup
-------

Only SQL\*Plus can be used to login to a closed database.  gqlplus hangs during the attempt.
The other tools simply report that the database is closed and cannot connect.

Text file editing
-----------------

In senora and YASQL, the `ed` and `\\e` commands (respectively) can be used to edit
text files using the environment's default editor.  Unlike SQL\*Plus, however, they
do not edit the *most recently issued command* (the buffer), and the resulting file
is not automatically run.  sqlpython's `ed`, without an argument, edits the SQL buffer 
as SQL\*Plus does, and runs the result when the editor is closed.  You may also 
`ed {filename}` to edit a specific text file, `ed {N}` to load command number {N} 
from the command history into the buffer and edit it.  Finally, if your EDITOR 
environment is not set, sqlpython tries to find a more user-friendly editing program 
on your machine than UNIX ed.

Hints
-----

sqlpython removes all comments from commands at an early stage of parsing, and thus 
will not honor execution hints embedded within SQL statements.

Variables
---------

YASQL does not support bind variables (`:` variables) or substitution variables (`&` variables).
The other tools support them, and sqlpython has enhanced bind variables (see above).

Parsing speed
-------------

sqlpython parses each line of a SQL command as it is entered to determine whether the command
is finished yet.  This produces noticable waits as a query approaches ten lines of SQL, and
downright annoying as it grows beyond that.  To avoid it, you can prefix long queries with
`REMARK BEGIN` and end them with `REMARK END`, promising sqlpython that you will only enclose a
single query and freeing it from the need to parse until `REMARK END` is reached.

Maturity
--------

All the alternate tools are produced by individuals or very small groups, so it is not
uncommon to encounter bugs.  If you encounter one, you can e-mail the author; 
for sqlpython in particular, error reports filed in the project's bug tracker at 
http://trac-hg.assembla.com/sqlpython are appreciated.  Since the projects are
open-source, and most of them are written in the easy-to-use languages Perl and Python, 
you can always fix bugs yourself and improve the products for everyone.

============
Installation
============

First, make sure you have Oracle client software on your machine!  gqlplus simply 
wraps SQL\*Plus, and wenora, YASQL, and
sqlpython depend on 
Perl or Python modules that access the Oracle OCI, so none of them will work in the absence of
an Oracle client.

You will also need Perl (for senora or YASQL) or Python (for sqlpython).  Virtually all UNIX
systems will have these languages installed, and frankly, every computer *should*.  Free installers for
all common platforms are available from the languages' websites at http://www.perl.org/  
and http://python.org/.

gqlplus
-------

Gqlplus is distributed as a gzipped tarball, downloadable from http://gqlplus.sourceforge.net/,
containing the C source code and a precompiled binary
for Linux.  To use on Linux, simply expand the tarball and run Linux/gqlplus; you may want to place
the file or a link to it somewhere in your PATH.  On other systems, you will a C compiler such 
as `gcc`; run `./configure` and `make` as directed in the project's `README` file.

Senora
------

Unix
~~~~

Senora is distributed as a gzipped tarball, downloadable from http://senora.sourceforge.net/

Senora depends on the DBI and DBD::Oracle packages.  Perl's `cpan` tool is a fairly convenient way 
to install them::

  $ cpan
  
  cpan> install DBI Term::ReadLine::Perl
  cpan> force install DBD::Oracle

If this is your first time running `cpan`, it will ask you many configuration questions
on startup.  Accepting the default answers is generally correct.  
Running under `sudo`, `cpan` may not find your $ORACLE_HOME; running as `root` avoids this problem.

After installation is complete, download and unzip Senora-0.5.1.tgz from http://senora.sourceforge.net/, cd into senora/core, and run `perl Senora.pm`.

Windows
~~~~~~~

http://senora.sourceforge.net/ also has a "Senora for Windows" download.  Download it, unzip, and
run `SenoraForWindows/senora.exe`.  You may wish to create a shortcut for your convenience.

YASQL
-----

Like senora, YASQL depends on the DBI and DBD::Oracle packages.  Several other Perl packages
are recommended and can also be installed through `cpan`::

  cpan> install DBI 
  cpan> force install DBD::Oracle
  cpan> install Term::ReadKey Text::CSV_XS Time::HiRes Term::ReadLine::Perl

Download yasql-1.83.tar.gz from http://sourceforge.net/projects/yasql/, unzip and untar it, and
cd into yasql-1.83.  Run `./configure`, `make`, and (as root) `make install`.
This will place the yasql executable into /usr/local/bin, so that you can run it from anywhere
by simply typing `yasql`.

sqlpython
---------

Some UNIX machines come shipped with Python but without python-dev, which you should install
from your distribution's package repository if you don't have it already.  Downloads from http://python.org
(including the Windows installer) include python-dev out of the box.

The easiest way to install sqlpython is with `easy_install`, a popular Python package installation
tool.  You can get easy_install by installing python-setuptools from your Linux distribution's repository,
or by downloading directly from http://peak.telecommunity.com/DevCenter/EasyInstall.

Once you have easy_install, simply type (as root, or using `sudo`)::

  $ easy_install -UZ sqlpython

The -UZ flags, though optional, will update your sqlpython installation, if necessary, and 
unzip the code so that you can modify it.

To generate graphs using sqlpython's `\\b`, `\\g`, and `\\l` terminators, you will need to install `pylab` (or `matplotlib`)::

  $ easy_install pylab

  $ apt-get install python-matplotlib
  
Alternately, a Windows installer is available at http://pypi.python.org/pypi/sqlpython, though easy_install
works on Windows as well.

===================
Extending the tools 
===================

All the alternative tools are open-source, so you have the right to view the source
code, make your own modifications, contribute your modifications back to the original
project, and even distribute your own modified version.  YASQL, senora, and sqlpython
are especially easy to modify since they are written in dynamic languages, which are
easy to program in and require no compilation step.

When you are ready to begin customizing or improving your favorite tool, imitation is
the key; look in the source code files of the tool for the code corresponding to a 
simple command, copy and rename it, then work on small modifications until the new
functionality meets your needs.

As a specific example, we will add new commands to sqlpython.  

`easy_install -UZ sqlpython` places sqlpython's source code files into your Python site-packages
directory, probably someplace like `/usr/lib/python2.5/site-packages/`.  You can edit the files there
(you may need to change their ownership from `root` to yourself first).  Any method in 
`mysqlpy` whose name begins with `do_` will be registered as a sqlpython
command the next time sqlpython is started.  The simplest possible new command could
be written as::

    def do_hello(self, arg):
        print 'Hello, World!'
        
Now, typing `hello [arguments]` in a sqlpython session calls `do_hello`.  The
optional arguments will be assigned to `arg`, but in this case they are not used.
Let's see a more useful function, one that will

* Make use of the argument string
  
* Provide online documentation
  
* Use a flag to optionally modify the command's behavior
  
* Send output to file, paste buffer, or pipe when `>` or `|` is used.
  
::

    @options([make_option('-u', '--uppercase', action='store_true', 
                          help='use ALL CAPS')])
    def do_greet(self, arg, opts):
        'Provides a personalized greeting.'
        result = 'Hello %s!\n' % arg
        if opts.uppercase:
            result = result.upper()
        self.stdout.write(result)
  
Now we run sqlpython and try the new command::

    jrrt@orcl> greet
    Hello !
    jrrt@orcl> greet Larry E.
    Hello Larry E.!
    jrrt@orcl> help greet
    Provides a personalized greeting.
    Usage: greet [options] arg
    
    Options:
      -h, --help       show this help message and exit
      -u, --uppercase  use ALL CAPS
    
    jrrt@orcl> greet -u World
    HELLO WORLD!

Senora v0.6 includes a command, `lregister`, that will automatically create a new senora plugin from
SQL commands in a file.  This will make an incredibly easy way to make your own senora 
commands for your favorite tasks.

=================
Cross-RDBMS tools
=================

All the tools reviewed so far have been designed purely for Oracle.  If you work with
multiple RDBMS platforms, however, you may be interested in a SQL tool that is compatible
with all of them, which opens up a whole new set of possible programs.

One such possibility is sqlcmd (http://www.clapper.org/software/python/sqlcmd),
an open-source Python program available without charge on all platforms.  It
operates seamlessly across Oracle, MySQL, PostreSQL, SQLite, and MS SQL Server.

Its functionality is rather basic compared to the Oracle-specific tools, and there
are conventions that will be unfamiliar to those immersed in an Oracle world.  For
example, use of stored procedures is not supported at all, column and table names
are case-sensitive, and database connection details are specified with an unfamiliar
format (`sqlcmd -d orcl,oracle,localhost,scott,tiger` in place of `sqlplus scott/tiger@orcl`).  Nonetheless, it and similar
tools are viable options when cross-RDBMS compatibility is a key requirement.
    
=======    
Summary
=======

All the tools offer capabilities that will make command-line interaction with Oracle easier and 
more powerful, and you should experiment to find out which one(s) suit you best.  If you want as
little change as possible, gqlplus provides a few extra features while being almost completely
transparent and SQL\*Plus-compatible.  Sqlpython has the broadest set of features and is
being developed most actively.  YASQL and senora may be good alternatives if you want some 
of the features unique to those programs, such as senora's rich set of tuning commands, 
or if you prefer Perl for writing your own improvements.  

There will always be a place for SQL\*Plus, but alternative tools
can replace and improve upon some of the work you have been doing both with SQL\*Plus
and with GUI tools.  No matter which programs you use, you will get more powerful, 
enjoyable commmand-line experiences and gain new appreciation for what open-source 
development can bring to an Oracle environment.

=====
Links
=====

* http://gqlplus.sourceforge.net/

* http://senora.sourceforge.net/

* http://sourceforge.net/projects/yasql/

* http://pypi.python.org/pypi/sqlpython

* http://www.clapper.org/software/python/sqlcmd

* http://catherinedevlin.blogspot.com/

================
Acknowledgements
================

Thanks to all the authors of the open-source tools reviewed here, but especially to Martin Drautzburg,
author of senora, for important corrections and additions.
