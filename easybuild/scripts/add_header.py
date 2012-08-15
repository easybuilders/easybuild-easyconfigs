#!/usr/bin/env python
##
# Copyright 2012 Jens Timmerman
# Copyright 2012 Kenneth Hoste
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
This script attempts to add a header to each file in the given directory 
The header will be put the line after a shebang (#!) if present.
If a line starting with a regular expression 'skip' is present as first line or after the shebang it will ignore that file.
If filename is given only files matching the filename regexp will be considered for adding the license to,
by default this is '*'

Usage: python addheader.py <header file> <directory> [<filename regexp> [<dirname regexp> [<skip regexp>]]]

easy example: add header to all files in this directory:
    python addheader.py licenseheader.txt . 

harder example, adding someone as copyright holder to all .py files in a source directory,except directories named 'includes' where he isn't added yet:
    python addheader.py licenseheader.txt src/ ".*\.py" "^((?!includes).)*$" "# Copyright .* Jens Timmerman*" 
where licenseheader.txt contains '# Copyright 2012 Jens Timmerman'
"""
import os
import re
import sys

def write_header(filename, header, skip=None):
    """
    write a header to filename, 
    skip files where first line after optional shebang matches the skip regex
    filename should be the name of the file to write to
    header should be a list of strings
    skip should be a regex
    """
    f = open(filename, "r")
    inpt = f.readlines()
    f.close()
    output = []
    # skip shebang line if it's there
    if len(inpt) > 0 and inpt[0].startswith("#!"):
        output.append(inpt[0])
        inpt = inpt[1:]

    if skip and inpt and skip.match(''.join(inpt)): # skip matches, so skip this file
        print "Skip regexp '%s' matches in %s, so skipping this file." % (skip.pattern, filename)
        return

    output.extend(header) # add the header
    for line in inpt:
        output.append(line)
    try:
        f = open(filename, 'w')
        f.writelines(output)
        f.close()
        print "added header to %s" % filename
    except IOError, err:
        print "something went wrong trying to add header to %s: %s" % (filename, err)

def add_header(directory, header, skipreg, filenamereg, dirregex):
    """
    recursively adds a header to all files in a dir
    arguments: see module docstring
    """
    listing = os.listdir(directory)
    print "listing: %s " % listing
    # for each file/dir in this dir
    for i in listing:
        # get the full name, this way subsubdirs with the same name don't get ignored
        fullfn = os.path.join(os.path.abspath(directory), i)
        basefn = os.path.basename(fullfn)
        if os.path.isdir(fullfn): # if dir, recursively go in
            if (dirregex.match(basefn)):
                print "going into %s" % fullfn
                add_header(fullfn, header, skipreg, filenamereg, dirregex)
        else:
            if (filenamereg.match(basefn)): # if file matches file regex, write the header
                write_header(fullfn, header, skipreg)
            else:
                print "Skipping file %s, doesn't match file regexp %s" % (fullfn, filenamereg.pattern)


def main(arguments):
    """
    main function: parses arguments and calls add_header
    """
    # argument parsing
    if len(arguments) > 6 or len(arguments) < 3:
        sys.stderr.write("Usage: %s <header file> <directory> [<filename regexp> [<dirname regexp> [<skip regexp>]]]\n" \
                         "Hint: '.*' is a catch all regex\nHint: '^((?!regexp).)*$' negates a regex\n" % sys.argv[0])
        sys.exit(1)

    # default skip regexp avoids readding the license header if it's already there
    skipreg = re.compile("[#\n]*#\s+Copyright\s+\d*")
    # only files that don't start with '.' and end with .py or .sh
    fileregex = "^((?!\.).)*\.(py|sh)$"
    # only paths that don't have subdirs that start with '.'
    dirregex = "^((?!\.).)*$"
    if len(arguments) > 5:
        skipreg = re.compile(arguments[5])
    if len(arguments) > 3:
        fileregex = arguments[3]
    if len(arguments) > 4:
        dirregex = arguments[4]
    # compile regex
    fileregex = re.compile(fileregex)
    dirregex = re.compile(dirregex)
    # read in the header file just once
    headerfile = open(arguments[1])
    header = headerfile.readlines()
    headerfile.close()
    add_header(arguments[2], header, skipreg, fileregex, dirregex)

# call the main method
main(sys.argv)
