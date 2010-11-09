try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
    def find_packages():
        return ['sqlpython']
    
classifiers = """Development Status :: 4 - Beta
Intended Audience :: Information Technology
License :: OSI Approved :: MIT License
Programming Language :: Python
Programming Language :: SQL
Topic :: Database :: Front-Ends
Operating System :: OS Independent""".splitlines()

setup(name="sqlpython",
      version="1.7.2",
      description="Command-line interface to Oracle",
      long_description="Customizable alternative to Oracle's SQL*PLUS command-line interface",
      author="Luca Canali",
      author_email="luca.canali@cern.ch",
      url="http://packages.python.org/sqlpython",
      packages=find_packages(),
      include_package_data=True,    
      install_requires=['pyparsing','cmd2>=0.6.2','gerald>=0.4.1.1',
                        'genshi>=0.5'],
      extras_require = {
        'oracle':  ['cx_Oracle>=5.0.2'],
        'postgres': ['psycopg2'],
        },
      keywords = 'client oracle database',
      license = 'MIT',
      platforms = ['any'],
      entry_points = """
                   [console_scripts]
                   sqlpython = sqlpython.mysqlpy:run
                   editplot_sqlpython = sqlpython.editplot.bash"""      
     )

