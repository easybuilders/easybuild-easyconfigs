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
import glob
import os
import sys
from distutils.version import LooseVersion

from optparse import OptionParser

from easybuild.framework.easyblock import EasyBlock


def find_easyconfig(path, name):
    # possible glob patterns
    possibles = [os.path.join(path, '*%s*.eb' % name),
                 os.path.join(path, name[0].lower(), "*%s*.eb" % name),
                 os.path.join(path, name[0].lower(), name, "*%s*.eb" % name)
                ]

    found = []
    for pos in possibles:
        found.extend(glob.glob(pos))

    return found

def main():
    parser = OptionParser()

    parser.add_option('-t', '--toolkit', help="toolkit name to use")
    parser.add_option('-v', '--version', default="", help="toolkit version to use")
    parser.add_option('-r', '--robot', help="path where other toolkits are stored")

    parser.add_option('-p', '--patches', action="append", help="list of patch files to use")

    (opts, args) = parser.parse_args()

    toolkit_files = find_easyconfig(opts.robot, opts.toolkit)

    if not toolkit_files:
        print "Could not find a suitable toolkit for specified toolkit: %s" % opts.toolkit
        sys.exit(1)

    # figure out the best toolkit to use
    toolkit_ebs = [EasyBlock(tk_file) for tk_file in toolkit_files]
    versions = [LooseVersion(tk['version']) for tk in toolkit_ebs]

    print "found the following versions for toolkit %s:" % toolkit_ebs[0]['name']
    for toolkit in toolkit_ebs:
        print toolkit.installversion()
    # if no version is specified we take the highest one, otherwise we take the closest one (which is still lower)
    wanted = LooseVersion(opts.version)
    if not opts.version:
        best = max(versions)
    else:
        best = max(filter(lambda v: v <= wanted, versions))

    # Select all the toolkits that match this version
    toolkits = [toolkit for toolkit in toolkit_ebs if LooseVersion(toolkit['version']) == best]
    if len(toolkits) > 1:
        print "found more than one toolkit which matches the specified version, checking for exact match"
        res = filter(lambda t: t.installversion() == opts.version, toolkits)
        if len(res) != 1:
            print "Consider specifying the version better (possibles: %s)" % [tk.installversion() for tk in toolkits]
            sys.exit(1)

        toolkit = res[0]
    else:
        toolkit = toolkits[0]

    print "using toolkit version: %s" % toolkit.installversion()

    # Toolkit has been found.
    for eb_file in args:
        eb = EasyBlock(eb_file, validate=False)
        eb['toolkit'] = {'name': toolkit['name'], 'version': toolkit.installversion()}

        filename = "%s-%s.eb" % (eb['name'], eb.installversion())
        new_eb = open(filename, 'w')

        new_eb.write("# File generated using change_toolkit.py\n")

        # check which vars are set inside the eb file
        vars = {}
        execfile(eb_file, {}, vars)

        # set patches, so it will definitly be included in the output
        if opts.patches:
            eb['patches'] = opts.patches
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
                    new_eb.write("%s = %s\n" % (var, repr(eb[var])))
                except:
                    pass

        new_eb.close()
        print "%s has been successfully written" % filename


if __name__ == '__main__':
    main()
