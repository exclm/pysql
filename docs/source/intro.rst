Introduction
============

* Original project homepage: https://twiki.cern.ch/twiki/bin/view/PSSGroup/SqlPython
* PyPI: http://pypi.python.org/pypi/sqlpython
* News: http://catherinedevlin.blogspot.com/search/label/sqlpython
* Current docs: http://packages.python.org/sqlpython/
* Mailing list: http://groups.google.com/group/sqlpython

SQLPython is a command-line interface to relational databases.  It was created as an alternative to Oracle's
``SQL\*Plus``, and can likewise be used instead of postgres' ``psql`` or mysql's ``mysql`` text clients.  
For the most part, it can be used as any other text-based SQL interface would; this document focuses on 
the extra capabilities.

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
(very unstable) has been moved from `assembla <https://www.assembla.com/wiki/show/sqlpython>`_
to `bitbucket <https://bitbucket.org/catherinedevlin/sqlpython>`;
you can install the trunk on your machine with::

  hg clone https://bitbucket.org/catherinedevlin/cmd2
	cd cmd2
	python setup.py develop

	cd ..
	hg clone https://bitbucket.org/catherinedevlin/sqlpython
	cd sqlpython
	python setup.py develop

Using `hg pull`, `hg update` subsequently will update from the current trunk.

You may also install from the trunk with easy_install::

  easy_install 
  
Finally, you will need database client software, access to a database server,
and the Python library corresponding to your chosen database(s):

Oracle
  `cx_Oracle <http://pypi.python.org/pypi/cx_Oracle>`
  
PostgreSQL
  `psycopg2 <http://pypi.python.org/pypi/psycopg2>`

MySQL
  `PyMySQL <http://pypi.python.org/pypi/PyMySQL>`
  

Running
-------

sqlpython [username[/password][@SID]] ["SQL command 1", "@script.sql", "SQL command 2..."]

or

sqlpython [--postgres|mysql] database-name username

Database connections can also be specified with URL syntax or with Oracle Easy Connect::

  oracle://username:password@SID
  
  oracle://username:password@hostname:port/dbname
  
  oracle://username:password@hostname:port/dbname
  
SID represents an entry from the `tnsnames.ora` file.  

Once connected, most familiar SQL\*Plus commands can be used.  Type `help` for additional
information.

Bugs
----

Please report bugs at http://www.assembla.com/spaces/sqlpython/tickets or to catherine.devlin@gmail.com.

Origins
-------

SQLPython is based on the Python standard library's 
`cmd <http://docs.python.org/library/cmd.html#module-cmd>`_ module, and on an extension 
to it called `cmd2 <http://pypi.python.org/pypi/cmd2>`_.  SQLPython also draws considerable
inspiration from two Perl-based open-source SQL clients, 
`Senora <http://senora.sourceforge.net/>`_ and `YASQL <http://sourceforge.net/projects/yasql>`_.

Non-Oracle RDBMS
----------------

Version 1.7.2 of sqlpython works against PostgreSQL and MySQL, though the testing against
those databases has been very slight thus far.  Help in testing and improving sqlpython's
functions against those databases is welcome.  Support for Microsoft SQL Server and sqlite
will be available as soon as those databases are added to the Gerald project, and volunteers
for Gerald will benefit sqlpython as well.