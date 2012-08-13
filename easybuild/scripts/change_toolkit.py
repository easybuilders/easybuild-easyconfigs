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


def find_easyconfig(path, name, version=""):
    # possible glob patterns
    possibles = [os.path.join(path, '*%s*%s*.eb' % (name, version)),
                 os.path.join(path, name[0].lower(), "*%s*%s*.eb" % (name, version)),
                 os.path.join(path, name[0].lower(), name, "*%s*%s*.eb" % (name, version))
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

    parser.add_option('-p', '--patches', action="store", help="list of patch files to use")

    (opts, args) = parser.parse_args()

    toolkit_files = find_easyconfig(opts.robot, opts.toolkit, opts.version)

    # if we don't find possible toolkits, we retry without specifying a version
    if not toolkit_files:
        toolkit_files = find_easyconfig(opts.robot, opts.toolkit)

    if not toolkit_files:
        print "Could not find a suitable toolkit for specified toolkit: %s" % opts.toolkit
        sys.exit(1)


    # figure out the best toolkit to use
    toolkit_ebs = [EasyBlock(tk_file) for tk_file in toolkit_files]

    # no version specified, we just take the most recent one
    if not opts.version:
        print toolkit_ebs[0]['name']
        print toolkit_ebs[0]['version']
        print toolkit_ebs[0].installversion()
        sys.exit(0)


    toolkit_ebs = filter(lambda eb: eb['name'] == opts.toolkit and LooseVersion(eb['version']) <
            LooseVersion(opts.version), toolkit_ebs)
    best_tk = toolkit_ebs[0]
    for tk_eb in toolkit_ebs:
        # exact match is always the best
        if tk_eb['name'] == opts.toolkit and tk_eb['version'] == opts.version:
            best_tk = tk_eb
            break
        # we have on which has a version closer than the current best
        elif LooseVersion(best_tk['version']) > LooseVersion(tk_eb['version']) >= LooseVersion(opts.version):
                best_tk = tk_eb

    print best_tk





if __name__ == '__main__':
    main()
