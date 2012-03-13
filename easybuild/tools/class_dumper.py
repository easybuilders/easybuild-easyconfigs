# coding=utf-8
import glob
import pyclbr
import os

def dumpClasses(root):
    """Get a class tree, starting at root"""
    moduleRoot=None
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
        if not classes.has_key(className):
            classes[className] = {'children': []}
        
        classes[className]['class'] = modules[className]

        parents = modules[className].super
        if len(parents) > 0:
            if type(parents[0]) != str:
                parent = parents[0].name
            else:
                parent = parents[0]

            if not classes.has_key(parent):
                classes[parent] = {'children': []}
            classes[parent]['children'].append(className)
        else:
            roots.append(className)

    # Print the tree, start with the roots
    for root in roots:
        print "%s (%s)" % (root, classes[root]['class'].module)
        if classes[root].has_key('children'):
            printTree(classes, classes[root]['children'])
            print ""

def printTree(classes, classNames, depth = 0):
    for className in classNames:
        classInfo = classes[className]
        print "%s├── %s (%s)" % ("│   " * depth, className, classInfo['class'].module)
        if classInfo.has_key('children'):
            printTree(classes, classInfo['children'], depth + 1)
    

if __name__ == "__main__":
    dumpClasses('easybuild.easyblocks')
