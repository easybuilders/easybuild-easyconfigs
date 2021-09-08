##
# Copyright 2012-2021 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
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
This script can be used to install easybuild-easyconfigs, e.g. using:
   easy_install --user .
 or
   python setup.py --prefix=$HOME/easybuild

@author: Kenneth Hoste (Ghent University)
"""

import os
from distutils import log
from distutils.core import setup

# note: release candidates should be versioned as a pre-release, e.g. "1.1rc1"
# 1.1-rc1 would indicate a post-release, i.e., and update of 1.1, so beware!
#
# important note: dev versions should follow the 'X.Y.Z.dev0' format
# see https://www.python.org/dev/peps/pep-0440/#developmental-releases
# recent setuptools versions will *TRANSFORM* something like 'X.Y.Zdev' into 'X.Y.Z.dev0', with a warning like
#   UserWarning: Normalizing '2.4.0dev' to '2.4.0.dev0'
# This causes problems further up the dependency chain...
VERSION = '4.4.2'

MAJ_VER = VERSION.split('.')[0]
MAJMIN_VER = '.'.join(VERSION.split('.')[0:2])

# log levels: 0 = WARN (default), 1 = INFO, 2 = DEBUG
log.set_verbosity(1)


# utility function to read README file
def read(fname):
    """Read contents of given file."""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


# utility function to get list of data files (i.e. easyconfigs)
def get_data_files():
    """
    Return list of data files, i.e. easyconfigs, patches, etc.,
    and retain directory structure.
    """
    data_files = []
    for dirname, dirs, files in os.walk(os.path.join('easybuild', 'easyconfigs')):
        if files:
            data_files.append((dirname, [os.path.join(dirname, f) for f in files]))
    return data_files


log.info("Installing version %s (required versions: API >= %s, easyblocks >= %s)" % (VERSION, MAJ_VER, MAJMIN_VER))

setup(
    name="easybuild-easyconfigs",
    version=VERSION,
    author="EasyBuild community",
    author_email="easybuild@lists.ugent.be",
    description="""Easyconfig files are simple build specification files for EasyBuild, \
that specify the build parameters for software packages (version, compiler toolchain, dependency \
versions, etc.).""",
    license="GPLv2",
    keywords="software build building installation installing compilation HPC scientific",
    url="https://easybuilders.github.io/easybuild/",
    data_files=get_data_files(),
    long_description=read("README.rst"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Build Tools",
    ],
    platforms="Linux",
    requires=[
        "easybuild_framework(>=%s.0)" % MAJ_VER,
        "easybuild_easyblocks(>=%s)" % MAJMIN_VER,
    ],
    # not known by distutils, but required to avoid that easy_install installs easyconfigs package as a zipped egg
    zip_safe=False,
)
