# The basic framework for adjusting the install location.
[ -z "$DESTDIR" ] && export DESTDIR="/"
[ -z "$PREFIX" ] && export PREFIX="/usr/local"
PREFIX="$DESTDIR/$PREFIX"

# This will just fail silently if we don't have write permissions for DESTDIR.
# That way, we can just leave the checking to the last minute.
[ ! -d "$PREFIX" ] && mkdir -p "$PREFIX" > /dev/null 2>&1

# Support for installing the Konqueror service menu
if which konqueror > /dev/null 2>&1; then
	if [ -w "$DESTDIR" ]; then
		[ -z "$KDEDIR" ] && KDEDIR="$DESTDIR/`cut -d: -f1 <<< \"$KDEDIRS\"`"
		[ -z "$KDEDIR" ] && KDEDIR="$PREFIX"
	else
		KDEDIR=~/.kde
	fi
	SERVICEMENU_DIR="${KDEDIR}/share/apps/konqueror/servicemenus"
fi

# Do the install.
if [ -w "$PREFIX" ] && [ "$1" != "--help" ] ; then
	[ -d "$PREFIX/bin" ] || mkdir -p "$PREFIX/bin"
	install src/unball "$PREFIX/bin/unball"

	if [ -n "$SERVICEMENU_DIR" ]; then
		[ -d "$SERVICEMENU_DIR" ] || mkdir -p "$SERVICEMENU_DIR"
		install --mode 0644 src/*.desktop "$SERVICEMENU_DIR"
		install src/moveToZip.sh "$PREFIX/bin/moveToZip.sh"
	fi
else
	[ "$1" != "--help" ] && echo "Sorry, it appears that you do not have write permissions for the chosen install location."
	echo "The install location can be adjusted using the DESTDIR and PREFIX environment variables."
	echo "There are three main ways to do this:"
	echo '  1. For making debs, rpms, or ebuilds: DESTDIR=$D PREFIX=/usr ./install.sh'
	echo '  2. As root (to put unball in /usr/bin): PREFIX=/usr ./install.sh'
	echo '  3. As a non-root user to install to your home directory: PREFIX=~ ./install.sh'
	echo "The default install location is /usr/local/bin"
fi
