import os


changes = {}

def write_changes(filename):
    """
    Write current changes to filename and reset environment afterwards
    """
    script = open(filename,'w')

    for key in changes:
        script.write('export %s="%s"\n' % (key, changes[key]))

    script.close()
    reset_changes()

def reset_changes():
    """
    Reset the changes tracked by this module
    """
    global changes
    changes = {}

def set(key, value):
    """
    put key in the environment with value
    tracks added keys until write_changes has been called
    """
    # os.putenv() is not necessary. os.environ will call this.
    os.environ[key] = value
    changes[key] = value
