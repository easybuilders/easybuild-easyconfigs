import re
import sys
import fileinput

"""This script removes instances of '.so' from easyconfigs, replacing
them with proper use of SHLIB_EXT.

Author: Elizabeth Fischer, 2016
        rpf2116@columbia.edu

Usage:
     python fixso `find . -name '*.eb'`
"""

doubleRE = re.compile('("([^"]*?)\\.so")|(\'([^\']*?)\\.so\')')

def fixso(fin):
	for line in fin:
		oline = []
		last_match_end = 0
		for match in doubleRE.finditer(line):
			groups = match.groups()
			if groups[0]:
				oline.append(line[last_match_end:match.start()])
				leavealone = ((groups[1]).find('%s') >= 0)
				if leavealone:
					oline.append(groups[0])
				else:
					oline.append(r'"{1:s}.%s" % SHLIB_EXT'.format(*groups))
				last_match_end = match.end()

			elif groups[2]:
				oline.append(line[last_match_end:match.start()])
				leavealone = ((groups[3]).find('%s') >= 0)
				if leavealone:
					oline.append(groups[3])
				else:
					oline.append('\'{3:s}.%s\' % SHLIB_EXT'.format(*groups))
				last_match_end = match.end()



		oline.append(line[last_match_end:])

		ol = ''.join(oline)
		sys.stdout.write(ol)

fixso(fileinput.FileInput(sys.argv[1:], inplace=1))
