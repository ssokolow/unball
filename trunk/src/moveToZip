#!/bin/sh
# moveToZip.sh v0.2
# By: Stephan Sokolow (deitarion/SSokolow)
# $Revision$

source unball --source # Why keep two copies of the abspath() function?

for FILE in "$@"; do
	srcdir=`realpath "${FILE%/}"`
	pushd "${srcdir%/*}" > /dev/null
	zip -rTm "${srcdir##*/}".zip "${srcdir##*/}"
	popd > /dev/null
done
