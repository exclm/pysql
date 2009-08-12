import shelve, pickle, cx_Oracle, datetime, sys, itertools
shelvename = 'plot.shelve'

try:
    import pylab
    class Plot(object):
        plottable_types = (cx_Oracle.NUMBER, datetime.datetime)    
        def __init__(self):
            self.legends = []
            self.yserieslists = []
            self.xticks = []
        def build(self, sqlSession, outformat):
            self.outformat = outformat
            self.title = sqlSession.tblname
            self.xlabel = sqlSession.curs.description[0][0]
            self.datatypes = [d[1] for d in sqlSession.curs.description]
            plottableSeries = [dt in self.plottable_types for dt in self.datatypes]
            if plottableSeries.count(True) == 0:
                raise ValueError, 'At least one quantitative column needed to plot.'
            elif len(plottableSeries) == 1: # only one column, but it is plottable
                idx = plottableSeries.index(True)
                self.yserieslists = [[row[0] for row in sqlSession.rows]]
                self.legends = [sqlSession.curs.description[0][0]]                
                self.xvalues = range(len(sqlSession.rows))
                self.xticks = [row[0] for row in sqlSession.rows]
            else:
                for (colNum, plottable) in enumerate(plottableSeries):
                    if colNum > 0 and plottable:
                        yseries = [row[colNum] for row in sqlSession.rows]
                        self.yserieslists.append(yseries)
                        self.legends.append(sqlSession.curs.description[colNum][0])
                if plottableSeries[0]:
                    self.xvalues = [r[0] for r in sqlSession.rows]
                else:
                    self.xvalues = range(sqlSession.curs.rowcount)
                    self.xticks = [r[0] for r in sqlSession.rows]
            
        def shelve(self):
            s = shelve.open(shelvename,'c')
            for k in ('xvalues xticks yserieslists title legends xlabel outformat'.split()):
                s[k] = getattr(self, k)
            s.close()
            # reading pickles fails with EOF error, don't understand
        def unshelve(self):
            s = shelve.open(shelvename)
            self.__dict__.update(s)
            s.close()
            self.draw()
        def bar(self):
            barEdges = pylab.arange(len(self.xvalues))
            width = 0.6 / len(self.yserieslists)
            colorcycler = itertools.cycle('rgb')
            for (offset, yseries) in enumerate(self.yserieslists):
                self.yplots.append(pylab.bar(barEdges + (offset*width), yseries, width=width, color=colorcycler.next()))
            pylab.xticks(barEdges + 0.3, self.xticks or self.xvalues)            
        def line(self, markers):
            for yseries in self.yserieslists:
                self.yplots.append(pylab.plot(self.xvalues, yseries, markers))
            if self.xticks:
                pylab.xticks(self.xvalues, self.xticks)
        def pie(self):
            self.yplots.append(pylab.pie(self.yserieslists[0], labels=self.xticks or self.xvalues))
            self.legends = [self.legends[0]]
        def draw(self):
            if not self.yserieslists:
                print 'At least one quantitative column needed to plot.'
                return None
            self.yplots = []
            if self.outformat == '\\l':
                self.line('-o')
            elif self.outformat == '\\L':
                self.line('o')
            elif self.outformat == '\\p':
                self.pie()
            else:
                self.bar()
            pylab.xlabel(self.xlabel)
            pylab.title(self.title)
            pylab.legend([p[0] for p in self.yplots], self.legends, shadow=True)
            pylab.show()
            print 'You can edit this plot from the command prompt (outside sqlpython) by running'
            print "ipython -pylab -c 'import sqlpython.plothandler; sqlpython.plothandler.Plot().unshelve()'"
            print "See matplotlib documentation for editing instructions: http://matplotlib.sourceforge.net/"
            # there's got to be a way to install a shell script like that through setuptools... but how?
            
except ImportError:
    class Plot(object):
        def __init__(self, *args, **kwargs):
            raise ImportError, 'Must install python-tk, python-matplotlib, and python-numpy to draw plots'

except Exception, e:
    class Plot(object):
        def __init__(self, *args, **kwargs):
            raise ImportError, 'There was a problem attempting to use plots:\n%s' % str(e)
