export PYTHONPATH=$PYTHONPATH:.
python setup.py install
python tests/unittest_pybikes.py $@
