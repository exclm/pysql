Introduction
============

SQLPython is a command-line interface to Oracle databases.  It is intended as an alternative to Oracle's
SQL\*Plus.  For the most part, it can be used the same way SQL\*Plus would be used; this documentation
focuses on the places where SQLPython differs.

SQLPython was created by `Luca Canali <http://canali.web.cern.ch/canali/>_` at CERN.  Most new development
has been done by `Catherine Devlin <http://catherinedevlin.blogspot.com/>_`.

SQLPython is based on the Python standard library's cmd module, and on an extension to it called cmd2.

SQLPython is currently only compatible with Oracle databases.  Expanding it to other RDBMS is a dream
for "one fine day".  Call it "SQLPython 3000".