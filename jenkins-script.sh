#!/bin/bash

export PATH=/tools/envmodules/modules-3.2.10/:$PATH

module load EasyBuild/3.4.0

eb $SOFTWARENAME --robot --use-existing-modules
