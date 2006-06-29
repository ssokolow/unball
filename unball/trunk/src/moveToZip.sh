#!/bin/sh

for FILE in "$@"; do
	srcdir="${FILE%/}"
	pushd "${FILE%/*}"
	zip -rTm "${srcdir##*/}".zip "${srcdir##*/}"
	popd
done
