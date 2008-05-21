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

