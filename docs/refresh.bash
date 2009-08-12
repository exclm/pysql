sphinx-build -b html source build
#scp -r build catherine@$tummy:/var/www/sqlpython
cd build
zip -r sqlpython_docs *
mv sqlpython_docs.zip ..
cd ..
echo "Upload sqlpython_docs.zip to http://pypi.python.org/pypi/sqlpython"
