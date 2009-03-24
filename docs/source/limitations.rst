===========
Limitations
===========

Bug reports and feature requests are welcome at 
`the project's bug tracker on Assembla <http://trac-hg.assembla.com/sqlpython/report>`_.

Slow parsing
------------

After each line of text in a multi-line command is entered, SQLPython pauses to determine whether
the command is finished yet.  This pause is unnoticable at first, but gradually becomes noticable,
then annoying, then crippling when very long commands are entered.

This problem can be worked around by bracketing long, individual commands in REMARK BEGIN 
and REMARK END statements.  When SQLPython finds a REMARK BEGIN, it stops parsing after each
line and assumes that everything entered until REMARK END is a single statement.

PL/SQL
------

SQLPython interprets short anonymous PL/SQL blocks correctly, as well as one-line PL/SQL
commands preceded with `exec`.  For longer blocks, however, it gets confused about where
the statement begins and ends.

To parse PL/SQL safely, enclose each free-standing PL/SQL block between a REMARK BEGIN and a
REMARK END statement.

Unsupported SQL\*Plus commands
------------------------------

(partial list)

* APPEND 

* ARCHIVE LOG

* ATTRIBUTE

* BREAK, BTITLE, CLEAR, COLUMN, COMPUTE, REPFOOTER, REPHEADER, and all SQL\*Plus report formatting commands.  In my opinion, special sqlpython output is much more powerful than SQL\*Plus report-formatting anyway.

* COPY (Consider using `cat {table} \\i > table.sql`, `connect -a me@otherplace`, then `@table.sql`)

* DEL

* DISCONNECT

* INPUT

* PASSWORD

* RECOVER

* SET APPINFO

* SET ARRAYSIZE

* SET AUTOCOMMIT (but should!)

* SET AUTOPRINT  (but should!)

* SET FEEDBACK OFF

* SET AUTOTRACE ON

* UNDEFINE

* VARIABLE (unneeded; bind variables can be set without pre-defining them)

* WHENEVER
