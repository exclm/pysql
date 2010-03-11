============
Design Notes
============

These design notes will hopefully not be necessary for routine use
of sqlpython; they describe implementation details intended to be
transparent to the user.  However, if you get involved in developing
or debugging - or if something goes wrong (which it sometimes will) -
this information may be of interest. 

Pickled metadata
----------------

sqlpython relies on Gerald to collect metadata, and this collection
takes some time.  When a database connection is made, a Gerald 
connection is initiated; to provide preliminary metadata before that
Gerald collection is complete, sqlpython looks for a picklefile
storing metadata collected during an earlier session.  When the fresh
metadata collection is complete, it is stored in pickled form for the
next session.




