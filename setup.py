from setuptools import setup, find_packages

classifiers = """Development Status :: 4 - Beta
Intended Audience :: Information Technology
License :: OSI Approved :: MIT License
Programming Language :: Python
Programming Language :: SQL
Topic :: Database :: Front-Ends
Operating System :: OS Independent""".splitlines()

setup(name="sqlpython",
      version="1.5.3",
      description="Command-line interface to Oracle",
      long_description="Customizable alternative to Oracle's SQL*PLUS command-line interface",
      author="Luca Canali",
      author_email="luca.canali@cern.ch",
      url="https://twiki.cern.ch/twiki/bin/view/PSSGroup/SqlPython",
      packages=find_packages(),
      include_package_data=True,    
      install_requires=['pyparsing','cmd2>=0.4.6','cx_Oracle','genshi>=0.5'],
      keywords = 'client oracle database',
      license = 'MIT',
      platforms = ['any'],
      entry_points = """
                   [console_scripts]
                   sqlpython = sqlpython.mysqlpy:run
                   editplot_sqlpython = sqlpython.editplot.bash"""      
     )

