##
# Copyright 2009-2012 Jens Timmerman
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
This module contains some usefull functions for getting system information
"""
import os
import re
from easybuild.tools.filetools import run_cmd

INTEL = 'Intel'
AMD = 'AMD'
VENDORS = {'GenuineIntel': INTEL, 'AuthenticAMD': AMD}

def get_core_count():
    """Try to detect the number of virtual or physical CPUs on this system.
    
    inspired by http://stackoverflow.com/questions/1006289/how-to-find-out-the-number-of-cpus-in-python/1006301#1006301
    """

    # Python 2.6+
    try:
        from multiprocessing import cpu_count
        return cpu_count()
    except (ImportError, NotImplementedError):
        pass

    # POSIX
    try:
        cores = int(os.sysconf('SC_NPROCESSORS_ONLN'))

        if cores > 0:
            return cores
    except (AttributeError, ValueError):
        pass

    # Linux
    try:
        res = open('/proc/cpuinfo').read().count('processor\t:')
        if res > 0:
            return res
    except IOError:
        pass

    # BSD
    try:
        out, _ = run_cmd('sysctl -n hw.ncpu')
        cores = int(out)

        if cores > 0:
            return cores
    except (ValueError):
        pass


    raise SystemException('Can not determine number of cores on this system')

def get_cpu_vendor():
    """Try to detect the cpu identifier
    will return INTEL or AMD
    """
    regexp = re.compile(r"^vendor_id\s+:\s*(?P<vendorid>\S+)\s*$", re.M)
    #linux
    try:
        arch = regexp.search(open("/proc/cpuinfo").read()).groupdict()['vendorid']
        if arch in VENDORS:
            return VENDORS[arch]
    except IOError:
        pass
    #osX
    out, exitcode = run_cmd("sysctl -n machdep.cpu.vendor")
    if not exitcode and out and out in VENDORS:
        return VENDORS[out]

    #bsd
    out, exitcode = run_cmd("sysctl -n hw.model")
    if not exitcode and out:
        return out.split(' ')[0]

    raise SystemException("Could not detect cpu vendor")

class SystemException(Exception):
    """raised when a system (os) specific thing went wrong"""

