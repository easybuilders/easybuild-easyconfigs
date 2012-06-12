#!/usr/bin/env python
##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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

# ensure lowercase module name
def rename_module(path):
    """Rename module is it's not lowercase."""
    try:
        if os.path.isfile(path):
            d = os.path.dirname(path)
            name = os.path.basename(path)
            print name
            if name != name.lower():
                shutil.move(os.path.join(d, name),
                            os.path.join(d, name.lower()))
                print "Module name was not lowercase, fixed that for you."
                return os.path.join(d, name.lower())
            else:
                print "Module naming OK."
                return path
        else:
            error("Specified easyblock %s not found!")
    except OSError, err:
        error("Failed to check module name: %s" % err)

# refactor function and argument names that have changed during cleanup
def refactor(txt):
    """Refactor given text, by refactoring function names, etc."""
    refactor_map = {
                    'addDependency':'add_dependency',
                    'addPatch':'addpatch',
                    'addSource':'addsource',
                    'apps.Application import Application':'framework.application import Application',
                    'applyPatch':'apply_patch',
                    'autoBuild':'autobuild',
                    'buildLog':'build_log',
                    'checkOsdeps':'check_osdeps',
                    'classDumper':'class_dumper',
                    'closeLog':'closelog',
                    'dumpConfigurationOptions':'dump_cfg_options',
                    'easybuild.buildsoft':'easybuild.tools',
                    'escapeSpecial':'escapespecial',
                    'extraPackages':'extra_packages',
                    'extraPackagesPre':'extra_packages_pre',
                    'fileLocate':'file_locate',
                    'fileTools':'filetools',
                    'filterPackages':'filter_packages',
                    'findPackagePatches':'find_package_patches',
                    'genInstallDir':'gen_installdir',
                    'getCfg':'getcfg',
                    'getInstance':'get_instance',
                    'importCfg':'process_ebfile',
                    'logall':'log_all',
                    'logok':'log_ok',
                    'makeBuildDir':'make_builddir',
                    'makeDir':'make_dir',
                    'makeInstall':'make_install',
                    'makeInstallDir':'make_installdir',
                    'makeInstallVersion':'make_installversion',
                    'makeModule':'make_module',
                    'makeModuleDescription':'make_module_description',
                    'makeModuleDep':'make_module_dep',
                    'makeModuleReq':'make_module_req',
                    'makeModuleReqGuess':'make_module_req_guess',
                    'makeModuleExtra':'make_module_extra',
                    'makeModuleExtraPackages':'make_module_extra_packages',
                    'moduleGenerator':'module_generator',
                    'parseDependency':'parse_dependency',
                    'readyToBuild':'ready2build',
                    'runrun':'run_cmd',
                    'runqanda':'run_cmd_qa',
                    'runTests':'runtests',
                    'runStep':'runstep',
                    'packagesFindSource':'find_package_sources',
                    'postProc':'postproc',
                    'sanityCheck':'sanitycheck',
                    'setCfg':'setcfg',
                    'setLogger':'setlogger',
                    'setNameVersion':'set_name_version',
                    'setParallelism':'setparallelism',
                    'setToolkit':'settoolkit',
                    'startFrom':'startfrom',
                    'unpackSrc':'unpack_src',
                    }

    totn = 0

    for old, new in refactor_map.items():

        regexp = re.compile("^(.*\W)%s(\W.*)$" % old, re.M)

        def repl(m):
            return "%s%s%s" % (m.group(1), new, m.group(2))

        (txt, n) = regexp.subn(repl, txt)
        totn += n

        print "%s => %s (%d), " % (old, new, n),

    print "\nreplaced %d names in total" % totn

    return txt

# check for use of Exception in except blocks, or lack of error class specification
def check_exception(txt):
    return txt

# 
# MAIN
# 

# fetch easyblock to check from command line
if len(sys.argv) == 2:
    easyblock = sys.argv[1]

else:
    error("Usage: %s <path>" % sys.argv[0])

# determine EasyBuild home dir, assuming this script is in <EasyBuild home>/easybuild/scripts
easybuild_home = os.path.sep.join(os.path.abspath(sys.argv[0]).split(os.path.sep)[:-3])

print "Found EasyBuild home: %s" % easybuild_home

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
print "Refactoring..."
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

if not all(all_checks):
    error("One or multiple checks have failed, easyblock %s is not fully cleaned up yet!" % easyblock)
