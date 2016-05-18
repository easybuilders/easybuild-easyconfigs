##
# Copyright 2012-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##

"""
This script can be used to install easybuild-easyblocks, e.g. using:
  easy_install --user .
or
  python setup.py --prefix=$HOME/easybuild

@author: Kenneth Hoste (Ghent University)
"""

import os
import re
import sys
from distutils import log

sys.path.append('easybuild')
from easyblocks import VERSION

API_VERSION = str(VERSION).split('.')[0]
suff = ''

rc_regexp = re.compile("^.*(rc[0-9]*)$")
res = rc_regexp.search(str(VERSION))
if res:
    suff = res.group(1)

dev_regexp = re.compile("^.*[0-9](.?dev[0-9])$")
res = dev_regexp.search(str(VERSION))
if res:
    suff = res.group(1)

API_VERSION += suff

# log levels: 0 = WARN (default), 1 = INFO, 2 = DEBUG
log.set_verbosity(1)

try:
    from setuptools import setup
    log.info("Installing with setuptools.setup...")
except ImportError, err:
    log.info("Failed to import setuptools.setup, so falling back to distutils.setup")
    from distutils.core import setup

# Utility function to read README file
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

log.info("Installing version %s (required versions: API >= %s)" % (VERSION, API_VERSION))

setup(
    name = "easybuild-easyblocks",
    version = str(VERSION),
    author = "EasyBuild community",
    author_email = "easybuild@lists.ugent.be",
    description = """Python modules which implement support for installing particular (groups of) software packages with EasyBuild.""",
    license = "GPLv2",
    keywords = "software build building installation installing compilation HPC scientific",
    url = "http://hpcugent.github.com/easybuild",
    packages = ["easybuild", "easybuild.easyblocks", "easybuild.easyblocks.generic"],
    package_dir = {"easybuild.easyblocks": "easybuild/easyblocks"},
    package_data = {'easybuild.easyblocks': ["[a-z0-9]/*.py"]},
    long_description = read("README.rst"),
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.4",
        "Topic :: Software Development :: Build Tools",
    ],
    platforms = "Linux",
    provides = ["easybuild", "easybuild.easyblocks", "easybuild.easyblocks.generic"],
    install_requires = [
        'setuptools >= 0.6',
        "easybuild-framework >= %s" % API_VERSION,
    ],
    zip_safe = False,
)
