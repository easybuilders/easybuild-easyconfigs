##
# Copyright 2012 Toon Willems
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
utility module for modifying os.environ
"""
import os

changes = {}

def write_changes(filename):
    """
    Write current changes to filename and reset environment afterwards
    """
    script = open(filename,'w')

    for key in changes:
        script.write('export %s="%s"\n' % (key, changes[key]))

    script.close()
    reset_changes()


def reset_changes():
    """
    Reset the changes tracked by this module
    """
    global changes
    changes = {}


def setvar(key, value):
    """
    put key in the environment with value
    tracks added keys until write_changes has been called
    """
    # os.putenv() is not necessary. os.environ will call this.
    os.environ[key] = value
    changes[key] = value
