#!/bin/sh

srcdir="${1%/}"
pushd "${1%/*}"
zip -rTm "${srcdir##*/}".zip "${srcdir##*/}"
popd

