
Summary:

This directory contains (hopefully) sufficient gear in order to let you
bootstrap towards the Lmod implementation of environment modules.

Howto:

Assuming you have successfully used the bootstrap procedure of EasyBuild,
you should be able to initiate a recursive build of the following bits:

l/Lmod/Lmod-5.2.5-GCC-4.8.2.eb
l/Lua/Lua-5.1.4-8-GCC-4.8.2.eb
n/ncurses/ncurses-5.9-GCC-4.8.2.eb
g/GCC/GCC-4.8.2.eb

This set is expected to be the needed substrate to launch you towards Lmod,
which gets activated with the script sitting in the same directory:

`source sourceme` # N.B. it does direct env. var. assignments; that's intentional

Then try:

`ml av` # ie. Lmod equivalent to `module avail`

You should now be able to try alternative Lmod/Lua versions, such as 3.x variety and so on so forth.

enjoy,
Fotis

2014-03-13
