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
Module with useful functions for getting system information
"""
import os
import re
from easybuild.tools.filetools import run_cmd


INTEL = 'Intel'
AMD = 'AMD'
VENDORS = {'GenuineIntel': INTEL, 'AuthenticAMD': AMD}


class SystemToolsException(Exception):
    """raised when systemtools fails"""

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


    raise SystemToolsException('Can not determine number of cores on this system')

def get_cpu_vendor():
    """Try to detect the cpu identifier

    will return INTEL or AMD
    """
    regexp = re.compile(r"^vendor_id\s+:\s*(?P<vendorid>\S+)\s*$", re.M)
    # Linux
    try:
        arch = regexp.search(open("/proc/cpuinfo").read()).groupdict()['vendorid']
        if arch in VENDORS:
            return VENDORS[arch]
    except IOError:
        pass
    # Darwin (OS X)

    out, exitcode = run_cmd("sysctl -n machdep.cpu.vendor")
    out = out.strip()
    if not exitcode and out and out in VENDORS:
        return VENDORS[out]

    # BSD
    out, exitcode = run_cmd("sysctl -n hw.model")
    out = out.strip()
    if not exitcode and out:
        return out.split(' ')[0]

    raise SystemToolsException("Could not detect cpu vendor")

def get_cpu_model():
    """
    returns cpu model
    f.ex Intel(R) Core(TM) i5-2540M CPU @ 2.60GHz
    """
    #linux
    regexp = re.compile(r"^model name\s+:\s*(?P<modelname>.+)\s*$", re.M)
    try:
        return regexp.search(open("/proc/cpuinfo").read()).groupdict()['modelname'].strip()
    except IOError:
        pass
    #osX
    out, exitcode = run_cmd("sysctl -n machdep.cpu.brand_string")
    out = out.strip()
    if not exitcode:
        return out

    return 'UNKNOWN'

def get_kernel_name():
    """Try to determine kernel name

    e.g., 'Linux', 'Darwin', ...
    """
    try:
        kernel_name = os.uname()[0]
        return kernel_name
    except OSError, err:
        raise SystemToolsException("Failed to determine kernel name: %s" % err)

def get_shared_lib_ext():
    """Determine extention for shared libraries

    Linux: 'so', Darwin: 'dylib' 
    """
    shared_lib_exts = {
                       'Linux':'so',
                       'Darwin':'dylib'
    }

    kernel_name = get_kernel_name()
    if kernel_name in shared_lib_exts.keys():
        return shared_lib_exts[kernel_name]

    else:
        raise SystemToolsException("Unable to determine extention for shared libraries," \
                                   " unknown kernel name: %s" % kernel_name)

def get_platform_name(withversion=False):
    """Try and determine platform name
    e.g., x86_64-unknown-linux, x86_64-apple-darwin
    """
    (kernel_name, _, release, _, machine) = os.uname()

    if kernel_name == 'Linux':
        vendor = 'unknown'
        release = '-gnu'
    elif kernel_name == 'Darwin':
        vendor = 'apple'
    else:
        raise SystemToolsException("Failed to determine platform name, unknown kernel name: %s" % kernel_name)

    if withversion:
        platform_name = '%s-%s-%s%s' % (machine, vendor, kernel_name.lower(), release)
    else:
        platform_name = '%s-%s-%s' % (machine, vendor, kernel_name.lower())

    return platform_name


