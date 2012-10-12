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
import glob
import pyclbr
import re
import os
import sys


def dump_classes(root, detailed=False):
    """Get a class tree, starting at root, by iterating of the PYTHONPATH."""

    rootpaths = []
    for path in sys.path:
        if path:  # skip ''
            rootpath = os.path.join(path, root.replace('.', '/'))
            if os.path.isdir(rootpath):
                rootpaths.append(path)

    print "rootpaths: %s" % rootpaths
 
    for rootpath in rootpaths:

        print "rootpath: %s" % rootpath

        # Read all modules
        modules = {}
        pyre = re.compile("^[^_].*\.py$")
        root = root.replace('.', '/')
        print os.path.join(rootpath, root)
        for (parent, _, files) in os.walk(os.path.join(rootpath, root)): #glob.glob(os.path.join(rootpath, root, '*.py')):
            print parent, files
            for moduleFile in files:
                if pyre.search(moduleFile):
                    module = '/'.join([parent, moduleFile])
                    print "module: %s" % module
                    module = '.'.join(module.split('.')[:-1])  # get rid of extension (.py)
                    print "readmodule(%s)" % module
                    modules.update(pyclbr.readmodule(module))

        modules.update(pyclbr.readmodule('easybuild.framework.easyblock'))
        modules.update(pyclbr.readmodule('easybuild.framework.extension'))
        print modules

        # Store parent-children relations
        classes = {}
        roots = []
        for className in sorted(modules):
            if not className in classes:
                classes[className] = {'children': []}

            classes[className]['class'] = modules[className]

            parents = modules[className].super
            if 'object' in parents:
                parents.remove('object')
            print "parents of %s: %s" % (className, parents)
            if len(parents) > 0:
                if type(parents[0]) != str:
                    parent = parents[0].name
                else:
                    parent = parents[0]

                if not parent in classes:
                    classes[parent] = {'children': []}
                classes[parent]['children'].append(className)
            else:
                roots.append(className)

        print classes

        # Print the tree, start with the roots
        for root in roots:
            if detailed:
                print "%s (%s)" % (root, classes[root]['class'].module)
            else:
                print "%s" % root
            if 'children' in classes[root]:
                print_tree(classes, classes[root]['children'], detailed)
                print ""

def print_tree(classes, classNames, detailed, depth=0):
    for className in classNames:
        classInfo = classes[className]
        if detailed:
            print "%s|-- %s (%s)" % ("|   " * depth, className, classInfo['class'].module)
        else:
            print "%s|-- %s" % ("|   " * depth, className)
        if 'children' in classInfo:
            print_tree(classes, classInfo['children'], detailed, depth + 1)


if __name__ == "__main__":
    dump_classes('easybuild.easyblocks')
