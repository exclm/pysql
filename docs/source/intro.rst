Introduction
============

* Original project homepage: https://twiki.cern.ch/twiki/bin/view/PSSGroup/SqlPython
* PyPI: http://pypi.python.org/pypi/sqlpython
* News: http://catherinedevlin.blogspot.com/search/label/sqlpython
* Current docs: http://packages.python.org/sqlpython/
* Mailing list: http://groups.google.com/group/sqlpython

SQLPython is a command-line interface to Oracle databases.  It is intended as an alternative to Oracle's
SQL\*Plus.  For the most part, it can be used the same way SQL\*Plus would be used; this documentation
focuses on the places where SQLPython differs.

License
-------

sqlpython is free and open-source software.  Its use is governed by the 
`MIT License <http://www.opensource.org/licenses/mit-license.php>`_.

Authorship
----------

SQLPython was created by `Luca Canali <http://canali.web.cern.ch/canali/>`_ at CERN.  Most recent
development has been done by `Catherine Devlin <http://catherinedevlin.blogspot.com/>`_.  A group
of additional sqlpython contributors has formed at 
`Google Groups <http://groups.google.com/group/sqlpython>`_.

Installation
------------

If `python-setuptools <http://pypi.python.org/pypi/setuptools>`_ is present on your machine, you
can easily install the latest release of sqlpython by issuing from a command prompt::

  easy_install sqlpython
  
The development trunk 
(very unstable) is at `assembla <https://www.assembla.com/wiki/show/sqlpython>`_; 
you can install the trunk on your machine with::

  hg clone http://hg.assembla.com/python-cmd2 cmd2
	cd cmd2
	python setup.py develop

	cd ..
	hg clone http://hg.assembla.com/sqlpython sqlpython
	cd sqlpython
	python setup.py develop

Using `hg pull`, `hg update` subsequently will update from the current trunk.

You may also install from the trunk with easy_install::

  easy_install 

Running
-------

sqlpython [username[/password][@SID]] ["SQL command 1", "@script.sql", "SQL command 2..."]

Database connections can also be specified with URL syntax or with Oracle Easy Connect::

  oracle://username:password@SID
  
  oracle://username:password@hostname:port/dbname
  
  oracle://username:password@hostname:port/dbname
  
SID represents an entry from the `tnsnames.ora` file.  

Once connected, most familiar SQL\*Plus commands can be used.  Type `help` for additional
information.

Bugs
----

Please report bugs at http://trac-hg.assembla.com/sqlpython or to catherine.devlin@gmail.com.

Origins
-------

SQLPython is based on the Python standard library's 
`cmd <http://docs.python.org/library/cmd.html#module-cmd>`_ module, and on an extension 
to it called `cmd2 <http://pypi.python.org/pypi/cmd2>`_.  SQLPython also draws considerable
inspiration from two Perl-based open-source SQL clients, 
`Senora <http://senora.sourceforge.net/>`_ and `YASQL <http://sourceforge.net/projects/yasql>`_.

Non-Oracle RDBMS
----------------

As of sqlpython 1.6.4, preliminary work has begun to adapt sqlpython to non-Oracle databases.
You may use it to run queries against postgreSQL, MySQL, etc., but data-dictionary access
commands (`ls`, `grep`, `refs`, etc.) will generate errors.  Connection to non-Oracle databases
is currently only possible via URL connection strings.

