import pyparsing, re, doctest
import logging

logging.basicConfig(filename='completion.log', level=logging.DEBUG)

sqlStyleComment = pyparsing.Literal("--") + pyparsing.ZeroOrMore(pyparsing.CharsNotIn("\n"))
keywords = {'order by': pyparsing.Keyword('order', caseless=True) +
                        pyparsing.Keyword('by', caseless=True),
            'select': pyparsing.Keyword('select', caseless=True),
            'from': pyparsing.Keyword('from', caseless=True),
            'having': pyparsing.Keyword('having', caseless=True),            
            'update': pyparsing.Keyword('update', caseless=True),
            'set': pyparsing.Keyword('set', caseless=True),            
            'delete': pyparsing.Keyword('delete', caseless=True),            
            'insert into': pyparsing.Keyword('insert', caseless=True) +
                           pyparsing.Keyword('into', caseless=True),
            'values': pyparsing.Keyword('values', caseless=True),
            'group by': pyparsing.Keyword('group', caseless=True) +
                        pyparsing.Keyword('by', caseless=True),
            'where': pyparsing.Keyword('where', caseless=True),
            'desc': pyparsing.Regex(r'^desc', flags=re.IGNORECASE),}
for (name, parser) in keywords.items():
    parser.ignore(pyparsing.sglQuotedString)
    parser.ignore(pyparsing.dblQuotedString)
    parser.ignore(pyparsing.cStyleComment)
    parser.ignore(sqlStyleComment)
    parser.name = name
   
fromClauseFinder = re.compile(r".*(from|update)(.*)(where|set)", 
                    re.IGNORECASE | re.DOTALL | re.MULTILINE)
oracleTerms = oracleTerms = re.compile(r"[A-Z$_#][0-9A-Z_$#]*", re.IGNORECASE)
def tableNamesFromFromClause(statement):
    result = fromClauseFinder.search(statement)
    if not result:
        return []
    result = oracleTerms.findall(result.group(2))
    result = [r.upper() for r in result if r.upper() not in ('JOIN','ON')]
    return result

def parse_results_in_order_of_appearance(parsers, statement):
    '''Results are ordered by index of their appearance in ``statement``, ascending
       (that is, early-in-statement to later-in-statement'''
    results = []
    for parser in parsers:
        results.extend(parser.scanString(statement))
    results.sort(cmp=lambda x,y:cmp(x[1],y[1]))
    return results

at_beginning = re.compile(r'^\s*\S+$')
def whichSegment(statement):
    '''
    >>> whichSegment("DESCRIBE ")
    'desc'
    >>> whichSegment("set ")
    'set'
    >>> whichSegment("SELECT col FROM t")
    'from'
    >>> whichSegment(r"  \dt ")
    'desc'
    >>> whichSegment("SELECT * FROM t")
    'from'
    >>> whichSegment("SELECT * FROM t groUP  by")
    'group by'
    >>> whichSegment("DES")
    'beginning'
    >>> whichSegment("")
    'beginning'
    >>> whichSegment("select  ")
    'select'
    '''
    if (not statement) or at_beginning.search(statement):
        return 'beginning'
    if statement.strip().startswith(r'\d'):
        return 'desc'
    results = parse_results_in_order_of_appearance(keywords.values(), statement)
    if results:
        result = ' '.join(results[-1][0])
        return result.lower()
    else:
        result = statement.split(None, 1)[0]
        return result.lower()

columnparser = re.compile(r'\bselect\s+(.*?)\s+from\b', re.IGNORECASE | re.DOTALL)  
sqlword = re.compile(r'[0-9a-zA-Z_#$]+')
def columnList(txt):
    '''
    >>> columnList('SELECT col1, col2, col3 FROM')
    ['col1', 'col2', 'col3']
    >>> columnList('select max(a), c.col2 - a.col1 from a, tab2 as c')
    ['max', 'a', 'c', 'col2', 'a', 'col1']
    '''
    match = columnparser.search(txt)
    if match:
        txt = match.group(1)
        words = sqlword.findall(txt)
        return words
    else:
        return []
        
reserved = '''
      access
     add
     all
     alter
     and
     any
     as
     asc
     audit
     between
     by
     char
     check
     cluster
     column
     comment
     compress
     connect
     create
     current
     date
     decimal
     default
     delete
     desc
     distinct
     drop
     else
     exclusive
     exists
     file
     float
     for
     from
     grant
     group
     having
     identified
     immediate
     in
     increment
     index
     initial
     insert
     integer
     intersect
     into
     is
     level
     like
     lock
     long
     maxextents
     minus
     mlslabel
     mode
     modify
     noaudit
     nocompress
     not
     nowait
     null
     number
     of
     offline
     on
     online
     option
     or
     order
     pctfree
     prior
     privileges
     public
     raw
     rename
     resource
     revoke
     row
     rowid
     rownum
     rows
     select
     session
     set
     share
     size
     smallint
     start
     successful
     synonym
     sysdate
     table
     then
     to
     trigger
     uid
     union
     unique
     update
     user
     validate
     values
     varchar
     varchar2
     view
     whenever
     where
     with '''.split()

if __name__ == '__main__':
    doctest.testmod()
