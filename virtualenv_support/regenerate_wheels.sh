set -eux

SETUPTOOLS=setuptools-12.0.5-py2.py3-none-any
rm $SETUPTOOLS.whl
cd $SETUPTOOLS
zip ../$SETUPTOOLS.whl -r *
cd ..
