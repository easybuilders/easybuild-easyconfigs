#!/usr/bin/env python
##
# Copyright 2012 Toon Willems
#
# This file is part of EasyBuild,
# originally created by the HPC-UGent team.
#
# http://github.com/easybuild/easybuild
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
#
##
"""
Script for automatically changing the toolkit of easyconfig files
"""
import glob
import os
import sys
from distutils.version import LooseVersion
from optparse import OptionParser

from easybuild.build import create_paths
from easybuild.framework.easyblock import EasyBlock


def find_easyconfig(path, name):
    """
    looks for easyconfigs with a given name in path
    """
    # possible glob patterns
    possibles = create_paths(path, name, "*")
    found = []
    for pos in possibles:
        found.extend(glob.glob(pos))

    return found


def main():
    """
    main entry point for script
    """
    parser = OptionParser()

    parser.add_option('-t', '--toolkit', help='toolkit name to use')
    parser.add_option('-n', '--name', help='package name')

    parser.add_option('-v', '--version', help='change software version to this')
    parser.add_option('--toolkit-version', default='', help='wanted toolkit version')
    parser.add_option('-r', '--robot', help='path where other toolkits are stored')

    parser.add_option('-p', '--patches', action='append', help='list of patch files to use')

    (opts, args) = parser.parse_args()

    toolkit_files = find_easyconfig(opts.robot, opts.toolkit)

    if not toolkit_files:
        print "Could not find a suitable toolkit for specified toolkit: %s" % opts.toolkit
        sys.exit(1)

    # figure out the best toolkit to use
    toolkit_ebs = [EasyBlock(tk_file) for tk_file in toolkit_files]
    versions = [LooseVersion(tk['version']) for tk in toolkit_ebs]

    print "found the following versions for toolkit %s:" % toolkit_ebs[0]['name']
    print "\n".join([toolkit.installversion() for toolkit in toolkit_ebs])

    # if no version is specified we take the highest one, otherwise we take the closest one (which is still lower)
    wanted = LooseVersion(opts.toolkit_version)
    if not opts.toolkit_version:
        best = max(versions)
    else:
        try:
            best = max(filter(lambda v: v <= wanted, versions))
        except:
            print "No version found lower than %s" % wanted
            sys.exit(1)

    # Select all the toolkits that match this version
    toolkits = [toolkit for toolkit in toolkit_ebs if LooseVersion(toolkit['version']) == best]
    if len(toolkits) > 1:
        print "found more than one possible toolkit for version %s, checking for exact match" % best
        res = filter(lambda t: t.installversion() == opts.toolkit_version, toolkits)
        if len(res) != 1:
            print "ERROR: no decisive toolkit version could be found"
            print "Consider specifying the version better (suggestions: %s)" % [tk.installversion() for tk in toolkits]
            sys.exit(1)

        toolkit = res[0]
    else:
        toolkit = toolkits[0]

    print "using toolkit version: %s" % toolkit.installversion()

    easyconfigs = find_easyconfig(opts.robot, opts.name)
    if not easyconfigs:
        print "Did not find an easyconfig for package: %s" % opts.name
        sys.exit(1)

    print "Found the following easyconfigs:"
    print '\n'.join(easyconfigs)

    easyconfigs = [EasyBlock(eb_file, validate=False) for eb_file in easyconfigs]

    # filter easyconfigs based on the version
    if opts.version:
        print "checking for easyconfigs with version %s" % opts.version
        same_version = filter(lambda eb: eb['version'] == opts.version, easyconfigs)
        if same_version:
            easyconfigs = same_version

    easyconfig_versions = set([eb['version'] for eb in easyconfigs])
    if len(easyconfig_versions) > 1:
        print "Found multiple versions for %s" % opts.name
        print "Consider specifying a version with --version (possibilities: %s)" % ', '.join(easyconfig_versions)
        sys.exit(1)

    if len(easyconfigs) > 1:
        print "finding optimal easyconfig file"
        same_toolkits = filter(lambda eb: eb.toolkit().name == opts.toolkit, easyconfigs)
        if same_toolkits:
            chosen = same_toolkits[0]
            print "found easyconfigs with same toolkit, using: %s" % '-'.join((chosen.name(), chosen.installversion()))
        else:
            chosen = easyconfigs[0]
            print "no easyconfig found with same toolkit, using %s" % '-'.join((chosen.name(), chosen.installversion()))
    else:
        chosen = easyconfigs[0]

    chosen['toolkit'] = {'name': toolkit['name'], 'version': toolkit.installversion()}

    # set version if specified
    if opts.version:
        chosen['version'] = opts.version

    filename = "%s-%s.eb" % (chosen['name'], chosen.installversion())
    new_eb = open(filename, 'w')

    new_eb.write("# File generated using change_toolkit.py\n")

    # check which vars are set inside the eb file
    vars = {}
    execfile(eb_file, {}, vars)

    # set patches, so it will definitly be included in the output
    if opts.patches:
        chosen['patches'] = opts.patches
        vars['patches'] = True

    # determine a pretty order
    order = ['name', 'version', '', 'homepage', 'description', '',  'toolkit', '', 'dependencies', '',
             'sources', 'sourceURLs', '']
    order.extend([var for var in vars if var not in order])

    for var in order:
        if var == '':
            new_eb.write("\n")
        else:
            try:
                new_eb.write("%s = %s\n" % (var, repr(chosen[var])))
            except:
                pass

    new_eb.close()
    print "%s has been successfully written" % filename


if __name__ == '__main__':
    main()
