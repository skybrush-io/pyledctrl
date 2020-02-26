#!/bin/sh
# 
# Compiles all the files found in data/simple/ and data/tests/

SCRIPT_ROOT=`dirname $0`

cd "${SCRIPT_ROOT}/../.."

for subdir in simple tests; do
	for fname in `find data/$subdir -name '*.led' -type f`; do
		if [ x`basename $fname | cut -c 1` = x_ ]; then
			# skip this file
			true
		else
			outfname="`echo $fname | sed -e 's/^data\//out\//' | sed -e 's/\.led$/.bin/'`"
			mkdir -p "`dirname $outfname`"
			bin/ledctrl compile --progress "$fname" -o "$outfname" "$@"
		fi
	done
done
