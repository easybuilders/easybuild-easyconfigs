#!/bin/sh
version=`python -V 2>&1 | sed 's/^Python \([0-9]*\)\.\([0-9]*\).*/\1.\2/'`

# See http://docs.python.org/using/cmdline.html#cmdoption-unittest-discover-m for -m support
export PYTHONPATH="`dirname $0`:$PYTHONPATH"
if [[ "$version" = "2.4" ]]; then
  python "`dirname $0`/easybuild/build.py" $@
else
  python -m easybuild.build $@
fi
