#!/usr/bin/python
# Copyright 2012 Jens Timmerman
#
#This file is part of EasyBuild.
#
#EasyBuild is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation v2.
#
#EasyBuild is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.

"""
This script attempts to add a header to each file in the given directory 
The header will be put the line after a Shebang (#!) if present.
If a line starting with a regular expression 'skip' is present as first line or after the shebang it will ignore that file.
If filename is given only files matchign the filename regex will be considered for adding the license to,
by default this is '*'

usage: python addheader.py headerfile directory [filenameregex [dirregex [skip regex]]]

easy example: add header to all files in this directory:
python addheader.py licenseheader.txt . 

harder example adding someone as copyrightholder to all python files in a source directory,exept directories named 'includes' where he isn't added yet:
python addheader.py licenseheader.txt src/ ".*\.py" "^((?!includes).)*$" "#Copyright .* Jens Timmerman*" 
where licenseheader.txt contains '#Copyright 2012 Jens Timmerman'
"""
import os
import re
import sys

def writeheader(filename,header,skip=None):
    """
    write a header to filename, 
    skip files where first line after optional shebang matches the skip regex
    filename should be the name of the file to write to
    header should be a list of strings
    skip should be a regex
    """
    f = open(filename,"r")
    inpt =f.readlines()
    f.close()
    output = []
    if len(inpt) > 0 and inpt[0].startswith("#!"): 
        output.append(inpt[0])
        inpt = inpt[1:]
        
    if skip and skip.match(inpt[0]): #skip matches, so skip this file
        return
    
    output.extend(header) #add the header
    for line in inpt:
        output.append(line)
    try:
        f = open(filename,'w')
        f.writelines(output)
        f.close()
        print "added header to %s" %filename
    except IOError,err:
        print "something went wrong trying to add header to %s: %s" % (filename,err)


def addheader(directory,header,skipreg,filenamereg,dirregex):
    """
    recursively adds a header to all files in a dir
    arguments: see module docstring
    """
    listing = os.listdir(directory)
    print "listing: %s " %listing
    #for each file/dir in this dir
    for i in listing:
        #get the full name, this way subsubdirs with the same name don't get ignored
        fullfn = os.path.join(directory,i) 
        if os.path.isdir(fullfn): #if dir, recursively go in
            if (dirregex.match(fullfn)):
                print "going into %s" % fullfn
                addheader(fullfn, header,skipreg,filenamereg,dirregex)
        else:
            if (filenamereg.match(fullfn)): #if file matches file regex, write the header
                writeheader(fullfn, header,skipreg)


def main(arguments=sys.argv):
    """
    main function: parses arguments and calls addheader
    """
    ##argument parsing
    if len(arguments) > 6 or len(arguments) < 3:
        sys.stderr.write("Usage: %s headerfile directory [filenameregex [dirregex [skip regex]]]\n" \
                         "Hint: '.*' is a catch all regex\nHint:'^((?!regexp).)*$' negates a regex\n"%sys.argv[0])
        sys.exit(1)
    
    skipreg = None
    fileregex = ".*"
    dirregex = ".*"
    if len(arguments) > 5:
        skipreg = re.compile(arguments[5])
    if len(arguments) > 3:
        fileregex =  arguments[3]
    if len(arguments) > 4:
        dirregex =  arguments[4]
    #compile regex    
    fileregex = re.compile(fileregex)
    dirregex = re.compile(dirregex)
    #read in the headerfile just once
    headerfile = open(arguments[1])
    header = headerfile.readlines()
    headerfile.close()
    addheader(arguments[2],header,skipreg,fileregex,dirregex)

#call the main method
main()