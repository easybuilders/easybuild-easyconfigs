##
# Copyright 2009-2012 Stijn De Weirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
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
import os


def dumpClasses(root):
    """Get a class tree, starting at root"""
    moduleRoot = None
    exec("from %s import __file__ as moduleRoot" % root)
    moduleRoot = os.path.dirname(moduleRoot) + '/'

    # Read all modules
    modules = {}
    for moduleFile in glob.glob(os.path.join(moduleRoot, '*.py')):
        module = "%s.%s" % (root, moduleFile.replace(moduleRoot, '').replace('.py', ''))
        modules.update(pyclbr.readmodule(module))

    # Store parent-children relations
    classes = {}
    roots = []
    for className in sorted(modules):
        if not className in classes:
            classes[className] = {'children': []}

        classes[className]['class'] = modules[className]

        parents = modules[className].super
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

    # Print the tree, start with the roots
    for root in roots:
        print "%s (%s)" % (root, classes[root]['class'].module)
        if 'children' in classes[root]:
            printTree(classes, classes[root]['children'])
            print ""

def printTree(classes, classNames, depth=0):
    for className in classNames:
        classInfo = classes[className]
        print "%s|-- %s (%s)" % ("|   " * depth, className, classInfo['class'].module)
        if 'children' in classInfo:
            printTree(classes, classInfo['children'], depth + 1)


if __name__ == "__main__":
    dumpClasses('easybuild.easyblocks')
