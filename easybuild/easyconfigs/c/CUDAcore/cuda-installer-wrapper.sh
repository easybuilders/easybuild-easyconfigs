#!/bin/bash
# Wrapper to use bwrap for more efficient installation of CUDA
# Use as cuda-installer to wrap cuda-installer.orig

instdir=""
for argument in "$@"; do
	if [[ $argument =~ ^--toolkitpath=.*$ ]]; then
		instdir=${argument/--toolkitpath=/}
	fi
done
if [[ -z "$instdir" ]]; then
	exit 1
fi

export instdir
export instdir_parent=$(dirname "$instdir")
export instdir_orig="$instdir_parent/orig"

rmdir $instdir
bwrap --dev-bind / / --tmpfs "$instdir_parent" --bind "$instdir_parent" "$instdir_orig" bash -c '
	./cuda-installer.orig "$@"
	for dir in "$instdir"/{bin,nvvm}; do setrpaths.sh --path "$dir"; done
	for dir in "$instdir"/{c,e,g,nsight,t}*; do setrpaths.sh --path "$dir" --add_origin; done
	mv "$instdir" "$instdir_orig"
' "$0" "$@"
