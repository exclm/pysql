SQLPython is an open-source command-line environment for interacting with an
Oracle database.  It is designed as an alternative to Oracle's SQL\*Plus.

Installing
----------

Debian/Ubuntu::

  $ sudo apt-get install python python-dev python-setuptools
  $ sudo easy_install cx_Oracle 
  $ sudo easy_install -UZ sqlpython

Windows:
Download and run executable installers from::

  http://www.python.org (Python language)
  http://cx-oracle.sourceforge.net/ (cx_Oracle)
  http://pypi.python.org/pypi/sqlpython (sqlpython) 

Other:
Python is typically already installed.  You'll need its
development package (python-dev); then easy_install
cx_Oracle and sqlpython as per Debian.

Using
-----

Use sqlpython more or less as you would use SQL\*Plus.  

Read the help.  Experiment with UNIX-style and postgresql-style
commands.

Special output (inspired by YASQL)
----------------------------------

An integer following a command terminator limits output to that number of rows, like SQL's LIMIT keyword::

  hr@xe> SELECT * FROM jobs;2
  
If `;` is replaced by one of these special characters, the output will be formatted as such::

----------  ----------------------
terminator  format
----------  ----------------------
;           standard Oracle format
\c          CSV (with headings)
\C          CSV (no headings)
\g          list
\G          aligned list
\h          HTML table
\i          INSERT statements
\s          CSV (with headings)
\S          CSV (no headings)
\t          transposed
\x          XML
----------  ----------------------

Special terminators can also be combined with row limits::

  hr@xe> SELECT * FROM jobs\h5  

Redirecting output
------------------

`>` and `>>` write or append the output of a command.  If a 
filename is given, that will be the destination of the output.

If no filename is given, the output will go into the paste buffer and
can immediately pasted to any program.  This requires `xclip` (*nix) or
`pywin32` (Windows) to be installed on the operating system.
  
Connecting
----------

sqlpython supports every version of connecting that SQL*Plus does, including EZCONNECT::

  $ > sqlpython
  $ > sqlpython hr/hr@xe  
  $ > sqlpython hr      (uses ORACLE_SID, prompts for password)
  $ > sqlpython hr/hr@hostmachine.somewhere.com/xe
  $ > sqlpython hr/hr@hostmachine.somewhere.com:1521/xe
  $ > sqlpython sys@xe as sysdba
  
You may also supply commands that will be run immediately after connection::

  $ > sqlpython hr/hr@xe @myscript.sql @another_script.sql quit

Multi-word commands must be enclosed in double-quotes::

  $ > sqlpython hr/hr@xe "cat jobs" "select * from employees;" 
  
Combining special output terminators with redirectors and command-line arguments
can produce powerful one-line programs.  For instance, this generates an HTML
report and exits::

  $ > sqlpython hr/hr@xe "select * from jobs\h > jobs.html" quit

Modifying
---------

Modify mysqlpy.py; add `do_mycommand(self, arg)` 
methods to the mysqlpy class to add your own commands.

Use `self.stdout.write(txt)` in place of `print txt` 
to make sure your output can be redirected into text 
files or the paste buffer with `>` and `>>`.

Contributing
------------

Development trunk is available from::

  http://www.assembla.com/wiki/show/sqlpython
  
Bugs and suggestions can be filed at::

  http://www.assembla.com/spaces/sqlpython/tickets

