#!/bin/sh
# 
# Compiles all the files found in data/

for fname in `find data -name '*.led' -type f`; do
	outfname="`echo $fname | sed -e 's/^data\//out\//' | sed -e 's/\.led$/.bin/'`"
	mkdir -p "`dirname $outfname`"
	bin/ledctrl compile "$fname" -o "$outfname" "$@"
done