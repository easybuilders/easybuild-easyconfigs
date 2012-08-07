#!/usr/bin/env python
##
# Copyright 2009-2012 Stijn De Weirdt
# Copyright 2010 Dries Verdegem
# Copyright 2010-2012 Kenneth Hoste
# Copyright 2011 Pieter De Baets
# Copyright 2011-2012 Jens Timmerman
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
This script checks a number of things to make sure the current codebase is ready for releasing a new version.
Things that are checked include:
- whether the current version number matches the last git version tag
- whether the RELEASE_NOTES have been updated for the current version
- whether all code files have a license header
- check for clean master branch

usage: prep_for_release.py
"""

import glob
import re
import os
import sys
from distutils.version import LooseVersion
try:
    import git
except ImportError, err:
    sys.stderr.write("Failed to import git Python module, which is required to run this script: %s\n" % err)
    sys.exit(1)


# error function (exits)
def error(msg):
    """Error function: print message to stderr and exit with non-zero exit code."""
    sys.stderr.write("ERROR: %s\n" % msg)
    sys.exit(1)

# warning function
def warning(msg):
    """Warning function: print message to stderr."""
    sys.stderr.write("WARNING: %s\n" % msg)

# determine EasyBuild version
def get_easybuild_version(home):
    """Determine current EasyBuild version, as set in init file."""

    initfile = os.path.join(home, "easybuild", "__init__.py")

    inittxt = None
    try:
        f = open(initfile, "r")
        inittxt = f.read()
        f.close()
    except IOError, err:
        error("Failed to read EasyBuild's init file at %s: %s" % (initfile, err))

    # determine current version set
    version_re = re.compile("^VERSION\s*=\s*[a-zA-Z(\"']*\s*(?P<version>[0-9.]+).*$", re.M)

    res = version_re.search(inittxt)

    if res:
        return LooseVersion(res.group('version'))
    else:
        error("Failed to determine EasyBuild version from %s (regexp pattern used: %s)." % (initfile, version_re.pattern))

# determine last git version tag
def get_last_git_version_tag(home):
    """Determine last git version tag."""

    try:
        gitrepo = git.Git(home)
        git_tags = gitrepo.execute(["git","tag","-l"]).split('\n')
        vertag_re = re.compile("^v([0-9]+\.[0-9]+)$")
        git_version_tags = [LooseVersion(vertag_re.match(t).group(1)) for t in git_tags if vertag_re.match(t)]
        if len(git_version_tags) >= 1:
            return git_version_tags[-1]
        else:
            error("No git version tags set?")

    except git.GitCommandError, err:
        error("Failed to determine last EasyBuild git tag: %s" % err)

# check whether EasyBuild version has been bumped and
# whether current git version tag matches current EasyBuild version
def check_version(easybuild_version, last_version_git_tag):
    """Check whether EasyBuild's version has been bumped."""

    print "Current EasyBuild version: %s" % easybuild_version
    print "Last git version tag: %s " % last_version_git_tag

    if not easybuild_version == last_version_git_tag:
        warning("Current EasyBuild version %s does not match last git version tag %s." % (easybuild_version, last_version_git_tag))
        return False
    else:
        print "Version checks passed."

        return True

# check whether RELEASE_NOTES have been updated
def check_release_notes(home, easybuild_version):
    """Check whether release notes have been updated."""

    fn = "RELEASE_NOTES"
    try:
        f = open(os.path.join(home, fn), "r")
        releasenotes = f.read()
        f.close()
    except IOError, err:
        error("Failed to read %s: %s" % (fn, err))

    ver_re = re.compile("^v%s\s\([A-Z][a-z]+\s[0-9]+[a-z]+\s[0-9]+\)$" % easybuild_version, re.M)

    if ver_re.search(releasenotes):
        print "Found entry in %s for version %s." % (fn, easybuild_version)
        return True
    else:
        warning("Could not find an entry for version %s in %s." % (easybuild_version, fn))
        return False

# check whether all code files have a license header
def check_license_headers(home, license_header_re, filename_re, dirname_re):
    """Check license header in all code files."""

    ok = True

    try:
        for d in os.listdir(home):
            # get the full name, this way subsubdirs with the same name don't get ignored
            fullfn = os.path.join(os.path.abspath(home), d)
            basefn = os.path.basename(fullfn)

            if os.path.isdir(fullfn): # if dir, recursively go in
                if (dirname_re.match(basefn)):
                    ok = check_license_headers(fullfn, license_header_re, filename_re, dirname_re)

            else:
                # check for license header in file
                if filename_re.match(basefn):
                    f = open(fullfn)
                    txt = f.read()
                    f.close()
                    if not license_header_re.search(txt):
                        warning("Could not find license header in %s" % fullfn)
                        ok - False

    except (OSError, IOError), err:
        error("Failed to check for license header in all code files: %s" % err)

    return ok

# check whether we're on the master branch, and whether it's clean
def check_clean_master_branch(home):
    """Check whether we're on the master branch, and whether it's clean (no outstanding commits)."""

    ok = True

    try:
        gitrepo = git.Git(home)
        git_status = gitrepo.execute(["git", "status"])

    except git.GitCommandError, err:
        error("Failed to determine status of git repository.")

    master_re = re.compile("^# On branch master$", re.M)
    clean_re = re.compile("^nothing to commit \(working directory clean\)$", re.M)

    if not master_re.search(git_status):
        warning("Make sure you're on the master branch when running this script.")
        ok = False
    else:
        print "On master branch, good."

    if not clean_re.search(git_status):
        warning("There seems to be work present that's not committed yet, please make sure the master branch is clear!")
        ok = False
    else:
        print "Current branch is clean, great work!"

    return ok

# check whether os.putenv or os.environ[]= is used inside easyblocks
def check_easyblocks_for_environment(home):
    """ check whether os.putenv or os.environ[]= is used inside easyblocks """

    files = glob.glob(os.path.join(home, 'easybuild/easyblocks/[a-z]/*.py'))
    eb_files = filter(lambda x: os.path.basename(x) != '__init__.py', files)

    os_env_re = re.compile("os\.environ\[\w+\]\s*=\s*")
    os_putenv_re = re.compile("os\.putenv")

    found = []
    for eb_file in eb_files:
        f = open(eb_file, "r")
        text = f.read()
        f.close()

        if os_putenv_re.search(text) or os_env_re.search(text):
            found.append(eb_file)

    for faulty in found:
        warning("found os.environ or os.putenv inside eb_file: %s" % faulty)

    if found:
        warning("Only easybuild.tools.environment.set should be used for setting environment variables.")

    return len(found) == 0


#
# MAIN
#

# determine EasyBuild home dir, assuming this script is in <EasyBuild home>/easybuild/scripts
easybuild_home = os.path.sep.join(os.path.abspath(sys.argv[0]).split(os.path.sep)[:-3])

print "Found EasyBuild home: %s" % easybuild_home

all_checks = []

# check EasyBuild version vs last git version tag
easybuild_version = get_easybuild_version(easybuild_home)
last_git_version_tag = get_last_git_version_tag(easybuild_home)

all_checks.append(check_version(easybuild_version, last_git_version_tag))

# check RELEASE_NOTES
all_checks.append(check_release_notes(easybuild_home, max(easybuild_version, last_git_version_tag)))

# check for license headers

license_header_re = re.compile("[#\n]*#\s+Copyright\s+\d*", re.M)
# only code files, i.e. that don't start with a '.', and end in either '.py' or '.sh'
filename_re = re.compile("^((?!\.).)*\.(py|sh)$")
# only paths that don't have subdirs that start with '.'
dirname_re = re.compile("^((?!\.).)*$")

print "Checking for license header in all code files..."
all_checks.append(check_license_headers(easybuild_home, license_header_re, filename_re, dirname_re))
print "Done!"

# check for clean master branch
all_checks.append(check_clean_master_branch(easybuild_home))
# check for use of os.putenv and os.environ adjustments
all_checks.append(check_easyblocks_for_environment(easybuild_home))

# check for use of os.putenv and os.environ adjustments
all_checks.append(check_easyblocks_for_environment(easybuild_home))

if not all(all_checks):
    error("One or multiple checks have failed, EasyBuild is not ready to be released!")
