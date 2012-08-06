#!/usr/bin/env python
##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
Script to port support for a particular software package to the new (public) version of EasyBuild,
which was clean up extensively.
It checks (and fixes, if needed and possible) whether:

 * module naming is lowercase only
 * refactoring has been done for all functions that have been renamed
    e.g. getCfg, setCfg, makeInstall, sanityCheck, runrun and runqanda (+ arguments)
 * Exception is no longer used and all except blocks catch specific errors only
 * the code is free of errors and warnings, according to PyLint
*

usage: check_code_cleanup.py
"""
import re
import os
import shutil
import sys

# error function (exits)
def error(msg):
    """Error function: print message to stderr and exit with non-zero exit code."""
    sys.stderr.write("ERROR: %s\n" % msg)
    sys.exit(1)

try:
    import pylint.lint
except ImportError:
    error("Failed to import PyLint module, I need it.")

# warning function
def warning(msg):
    """Warning function: print message to stderr."""
    sys.stderr.write("WARNING: %s\n" % msg)

# ensure lowercase module name
def rename_module(path):
    """Rename module is it's not lowercase."""
    try:
        if os.path.isfile(path):
            d = os.path.dirname(path)
            name = os.path.basename(path)
            if name != name.lower():
                shutil.move(os.path.join(d, name),
                            os.path.join(d, name.lower()))
                warning("Module name was not lowercase, fixed that for you.")
                return os.path.join(d, name.lower())
            else:
                print "Module naming OK.\n"
                return path
        else:
            error("Specified easyblock %s not found!")
    except OSError, err:
        error("Failed to check module name: %s" % err)

# refactor function and argument names that have changed during cleanup
def refactor(txt):
    """Refactor given text, by refactoring function names, etc."""
    refactor_map = {
                    'addDependency': 'add_dependency',
                    'addPatch': 'addpatch',
                    'addSource': 'addsource',
                    'apps.Application import Application': 'framework.application import Application',
                    'applyPatch': 'apply_patch',
                    'autoBuild': 'autobuild',
                    'buildInInstallDir': 'build_in_installdir',
                    'buildLog': 'build_log',
                    'checkOsdeps': 'check_osdeps',
                    'classDumper': 'class_dumper',
                    'closeLog': 'closelog',
                    'dumpConfigurationOptions': 'dump_cfg_options',
                    'easybuild.buildsoft': 'easybuild.tools',
                    'escapeSpecial': 'escapespecial',
                    'extraPackages': 'extra_packages',
                    'extraPackagesPre': 'extra_packages_pre',
                    'fileLocate': 'file_locate',
                    'fileTools': 'filetools',
                    'filterPackages': 'filter_packages',
                    'findPackagePatches': 'find_package_patches',
                    'genInstallDir': 'gen_installdir',
                    'getCfg': 'getcfg',
                    'getSoftwareRoot': 'get_software_root',
                    'getInstance': 'get_instance',
                    'importCfg': 'process_ebfile',
                    'logall': 'log_all',
                    'logok': 'log_ok',
                    'logOutput': 'log_output',
                    'makeBuildDir': 'make_builddir',
                    'makeDir': 'make_dir',
                    'makeInstall': 'make_install',
                    'makeInstallDir': 'make_installdir',
                    'makeInstallVersion': 'make_installversion',
                    'makeModule': 'make_module',
                    'makeModuleDescription': 'make_module_description',
                    'makeModuleDep': 'make_module_dep',
                    'makeModuleReq': 'make_module_req',
                    'makeModuleReqGuess': 'make_module_req_guess',
                    'makeModuleExtra': 'make_module_extra',
                    'makeModuleExtraPackages': 'make_module_extra_packages',
                    'moduleGenerator': 'module_generator',
                    'noqanda=': 'no_qa=',
                    'parseDependency': 'parse_dependency',
                    'readyToBuild': 'ready2build',
                    'runrun': 'run_cmd',
                    'runqanda': 'run_cmd_qa',
                    'runTests': 'runtests',
                    'runStep': 'runstep',
                    'packagesFindSource': 'find_package_sources',
                    'postProc': 'postproc',
                    'sanityCheck': 'sanitycheck',
                    'setCfg': 'setcfg',
                    'setLogger': 'setlogger',
                    'setNameVersion': 'set_name_version',
                    'setParallelism': 'setparallelism',
                    'setToolkit': 'settoolkit',
                    'startFrom': 'startfrom',
                    'stdqa=': 'std_qa=',
                    'unpackSrc': 'unpack_src',
                    }

    totn = 0

    print "Refactoring..."

    for old, new in refactor_map.items():

        regexp = re.compile("^(.*\W)%s(\W.*)$" % old, re.M)

        def repl(m):
            return "%s%s%s" % (m.group(1), new, m.group(2))

        (txt, n) = regexp.subn(repl, txt)
        totn += n

        print "%s => %s (%d), " % (old, new, n),

    print ""

    if totn > 0:
        warning("replaced %d names in total\n" % totn)
    else:
        print "replaced %d names in total\n" % totn

    return txt

# check for use of Exception in except blocks, or lack of error class specification
def check_exception(txt):
    """Check for lack of error specification in except block, or use of general Exception class."""

    print "Checking except blocks..."

    empty_except_re = re.compile("except\s*:")
    exception_re = re.compile("except\s*Exception")

    if empty_except_re.search(txt) or exception_re.search(txt):
        warning("One or multiple except blocks found that don't specify an error class or use Exception.\n")
        return False
    else:
        print "All except blocks seem to be OK!\n"
        return True

# inspiration: http://stackoverflow.com/questions/2028268/invoking-pylint-programmatically

# dummy output stream for PyLint
class WritableObject(object):
    "dummy output stream for PyLint"
    def __init__(self):
        self.content = []
    def write(self, st):
        "dummy write"
        self.content.append(st)
    def read(self):
        "dummy read"
        return self.content

# check whether PyLint still reports warnings or error
def run_pylint(fn):

    from pylint.reporters.text import TextReporter

    print "checking for PyLint warnings or errors..."

    # run PyLint on file, catch output
    pylint_output = WritableObject()
    pylint.lint.Run([fn, "-r", "n"], reporter=TextReporter(pylint_output), exit=False)

    # count number of warnings/errors
    warning_re = re.compile("^W:")
    error_re = re.compile("^E:")

    # warnings/errors we choose to ignore
    ignores_re = [
                  re.compile("^W:\s*[0-9,]*:[A-Za-z0-9_]*.configure: Arguments number differs from overridden method"),
                  re.compile("^W:\s*[0-9,]*:[A-Za-z0-9_]*.make: Arguments number differs from overridden method")
                  ]

    warning_cnt = 0
    error_cnt = 0
    for line in pylint_output.read():
        ignore = False
        for ignore_re in ignores_re:
            if ignore_re.match(line):
                print "Ignoring %s" % line
                ignore = True
        if ignore:
            continue
        # check for warnings
        if warning_re.match(line):
            warning("PyLint: %s" % line)
            warning_cnt += 1
        # check for errors
        if error_re.match(line):
            warning("PyLint: %s" % line)
            error_cnt += 1

    print
    if warning_cnt > 0 or error_cnt > 0:
        warning("PyLint is still reporting warnings (%d) and/or errors (%d).\n" % (warning_cnt, error_cnt))
        return False

    else:
        print "No warnings or errors reported by PyLint we care about, nice job!\n"
        return True

# MAIN
#

# fetch easyblock to check from command line
if len(sys.argv) == 2:
    easyblock = sys.argv[1]

else:
    error("Usage: %s <path>" % sys.argv[0])

# determine EasyBuild home dir, assuming this script is in <EasyBuild home>/easybuild/scripts
easybuild_home = os.path.sep.join(os.path.abspath(sys.argv[0]).split(os.path.sep)[:-3])

print "Found EasyBuild home: %s\n" % easybuild_home

# rename module if needed
easyblock = rename_module(easyblock)

# read easyblock
try:
    f = open(easyblock, "r")
    easyblock_txt = f.read()
    f.close()
except IOError, err:
    error("Failed to read easyblock %s: %s" % (easyblock, err))

# refactor
easyblock_txt = refactor(easyblock_txt)

all_checks = []

# check for use of Exception (or no error class at all)
all_checks.append(check_exception(easyblock_txt))

# write back refactored easyblock code
try:
    f = open(easyblock, "w")
    f.write(easyblock_txt)
    f.close()
except IOError, err:
    error("Failed to write refactored easyblock %s: %s" % (easyblock, err))

# check for PyLint warnings/errors
all_checks.append(run_pylint(easyblock))

if not all(all_checks):
    error("One or multiple checks have failed, easyblock %s is not fully cleaned up yet!" % easyblock)
