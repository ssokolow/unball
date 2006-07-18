# The basic framework for adjusting the install location.
[ -z "$DESTDIR" ] && DESTDIR="/" && export DESTDIR
[ -z "$PREFIX" ] && PREFIX="/usr/local" && export PREFIX
NAUTILUS_SCRIPT_SUFFIX="" # Set this to use hierarchical categories for Nautilus scripts.
UNBALL_TARGET="$PREFIX/bin/unball"
MOVETOZIP_TARGET="$PREFIX/bin/moveToZip.sh"

function install_nautilus() {
	# Usage: install_nautilus <UID> <GID> <HOMEDIR>
	# Purpose: Install unball and MoveToZip into the Nautilus scripts menu.

	# Find the script dir if it exists. Return if it doesn't.
	if [ -d "$3/.gnome2/nautilus-scripts" ]; then NSCRIPT_PATH="$3/.gnome2/nautilus-scripts"
	elif [ -d "$3/.gnome/nautilus-scripts" ]; then NSCRIPT_PATH="$3/.gnome/nautilus-scripts"
	elif [ -d "$3/Nautilus/scripts" ]; then NSCRIPT_PATH="$3/Nautilus/scripts"
	else return 1
	fi
	
	# Make the script category dir if it doesn't exist
	NSCRIPT_FULL_PATH="$DESTDIR/$NSCRIPT_PATH/$NAUTILUS_SCRIPT_SUFFIX"
	[ ! -d "$NSCRIPT_FULL_PATH" ] && mkdir -p "$NSCRIPT_FULL_PATH" &> /dev/null
	
	# Install the symlinks
	pushd "$NSCRIPT_FULL_PATH" > /dev/null
		ln -s "$UNBALL_TARGET" ./Unball
		chown "$1:$2" ./Unball
		ln -s "$MOVETOZIP_TARGET" "./Move to ZIP"
		chown "$1:$2" "./Move to ZIP"
	popd > /dev/null
}

function user_enum() {
	# Usage: user_enum <command>
	# command will receive <UID> <GID> <HOMEDIR> as it's parameters
	#FIXME: This will break if the homedir path contains spaces.
	for LINE in `cut -sd: -f3,4,6 /etc/passwd`; do
		LINE_SPLIT=`echo $LINE | tr ":" " "`
		$1 $LINE_SPLIT # DON'T just quote the $LINE_SPLIT. It has to expand into 3 positional args.
	done
}

# This will just fail silently if we don't have write permissions for DESTDIR.
# That way, we can just leave the checking to the last minute.
[ ! -d "$DESTDIR/$PREFIX" ] && mkdir -p "$DESTDIR/$PREFIX" &> /dev/null

# Support for installing the Konqueror service menu
if which konqueror &> /dev/null; then
	if [ -w "$DESTDIR" ]; then
		[ -z "$KDEDIR" ] && KDEDIR="$DESTDIR/`cut -d: -f1 <<< \"$KDEDIRS\"`"
		[ -z "$KDEDIR" ] && KDEDIR="$DESTDIR/$PREFIX"
	else
		KDEDIR=~/.kde
	fi
	SERVICEMENU_DIR="${KDEDIR}/share/apps/konqueror/servicemenus"
fi

# Do the install.
if [ -w "$DESTDIR/$PREFIX" ] && [ "$1" != "--help" ] ; then
	# Install unball
	[ -d "$DESTDIR/PREFIX/bin" ] || mkdir -p "$DESTDIR/$PREFIX/bin"
	install src/unball "$DESTDIR/$UNBALL_TARGET"

	# Install the Konqueror hooks
	if [ -n "$SERVICEMENU_DIR" ]; then
		[ -d "$SERVICEMENU_DIR" ] || mkdir -p "$SERVICEMENU_DIR"
		install --mode 0644 src/servicemenus/*.desktop "$SERVICEMENU_DIR"
		install src/moveToZip.sh "$DESTDIR/$MOVETOZIP_TARGET"
	fi

	# Install the Nautilus hook, but only if it doesn't already exist.
	# This ensures that users won't have unball re-added if they removed it after a previous install.
	NAUTILUS_SKEL_TARGET="/etc/skel/.gnome2/nautilus-scripts"
	if [ ! -L "$NAUTILUS_SKEL_TARGET/Unball" ]; then
		mkdir -p "$DESTDIR/$NAUTILUS_SKEL_TARGET"
		ln -s "$UNBALL_TARGET" "$DESTDIR/$NAUTILUS_SKEL_TARGET/Unball"
		ln -s "$MOVETOZIP_TARGET" "$DESTDIR/$NAUTILUS_SKEL_TARGET/Move to ZIP"
		user_enum install_nautilus
	fi

	echo "unball installed. You can now type \"./run_test.py\" to run the unit tests. If tests fail, you probably are missing some extraction tools."
	echo "Note: In this version of unball, there are six tests which always fail: Three for ziptest_bz2.zip, and three for ziptest_ppmd.zip."
else
	[ "$1" != "--help" ] && echo "Sorry, it appears that you do not have write permissions for the chosen install location."
	echo "The install location can be adjusted using the DESTDIR and PREFIX environment variables."
	echo "There are three main ways to do this:"
	echo '  1. For making debs, rpms, or ebuilds: DESTDIR=$D PREFIX=/usr ./install.sh'
	echo '  2. As root (to put unball in /usr/bin): PREFIX=/usr ./install.sh'
	echo '  3. As a non-root user to install to your home directory: PREFIX=~ ./install.sh'
	echo "The default install location is /usr/local/bin"
	echo
	echo "Also, if you prefer to sort your Nautilus scripts into categories, you can set the NAUTILUS_SCRIPT_SUFFIX variable."
fi
