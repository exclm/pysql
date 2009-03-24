import pyparsing, re

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
            'where': pyparsing.Keyword('where', caseless=True)}
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
    
def orderedParseResults(parsers, statement):
    results = []
    for parser in parsers:
        results.extend(parser.scanString(statement))
    results.sort(cmp=lambda x,y:cmp(x[1],y[1]))
    return results
        
def whichSegment(statement):
    results = orderedParseResults(keywords.values(), statement)
    if results:
        return ' '.join(results[-1][0])
    else:
        return None

oracleIdentifierCharacters = pyparsing.alphanums + '_#$'    
def wordInProgress(statement):
    result = []
    letters = list(statement)
    letters.reverse()
    for letter in letters:
        if letter not in oracleIdentifierCharacters:
            result.reverse()
            return ''.join(result)
        result.append(letter)
    result.reverse()
    return ''.join(result)
    