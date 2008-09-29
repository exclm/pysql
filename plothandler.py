import shelve, pickle, cx_Oracle, datetime, sys
shelvename = 'plot.shelve'

try:
    import pylab
    class Plot(object):
        plottable_types = (cx_Oracle.NUMBER, datetime.datetime)    
        def __init__(self):
            self.legends = []
            self.yserieslists = []
            self.xticks = []
        def build(self, sqlSession):
            self.title = sqlSession.tblname
            self.xlabel = sqlSession.curs.description[0][0]
            self.datatypes = [d[1] for d in sqlSession.curs.description]
            for (colNum, datatype) in enumerate(self.datatypes):
                if colNum > 0 and datatype in self.plottable_types:
                    yseries = [row[colNum] for row in sqlSession.rows]
                    if max(yseries) is not None:
                        self.yserieslists.append(yseries)
                        self.legends.append(sqlSession.curs.description[colNum][0])
            if self.datatypes[0] in self.plottable_types:
                self.xvalues = [r[0] for r in sqlSession.rows]
            else:
                self.xvalues = range(sqlSession.curs.rowcount)
                self.xticks = [r[0] for r in sqlSession.rows]
        def shelve(self):
            s = shelve.open(shelvename,'c')
            for k in ('xvalues xticks yserieslists title legends xlabel'.split()):
                s[k] = getattr(self, k)
            s.close()
            # reading pickles fails with EOF error, don't understand
        def unshelve(self):
            s = shelve.open(shelvename)
            self.__dict__.update(s)
            s.close()
            self.draw()            
        def draw(self):
            if not self.yserieslists:
                print 'At least one quantitative column needed to plot.'
                return None
            for yseries in self.yserieslists:
                pylab.plot(self.xvalues, yseries, '-o')
            if self.xticks:
                pylab.xticks(self.xvalues, self.xticks)
            pylab.xlabel(self.xlabel)
            pylab.title(self.title)
            pylab.legend(self.legends)
            pylab.show()
            
except ImportError:
    class Plot(object):
        def build(self, sqlSession):
            pass
        def save(self):
            pass
        def draw(self):
            return 'Must install python-matplotlib to plot query results.'