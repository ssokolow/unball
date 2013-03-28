#!/usr/bin/env bash

# The basic framework for adjusting the install location.
NAUTILUS_SCRIPT_SUFFIX="" # Set this to use hierarchical categories for Nautilus scripts.

function install_nautilus() {
	# Usage: install_nautilus <UID> <GID> <HOMEDIR>
	# Purpose: Install unball and MoveToZip into the Nautilus (GNOME) scripts menu.

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

# Do the install.
if [ -w "$DESTDIR/$PREFIX" ] && [ "$1" != "--help" ] ; then
	# Install manpages
	gen_manpages src/unball src/moveToZip

	# Install the Nautilus (GNOME) hook, but only if it doesn't already exist.
	# This ensures that users won't have unball re-added if they removed it after a previous install.
	NAUTILUS_SKEL_TARGET="/etc/skel/.gnome2/nautilus-scripts"
	if [ ! -L "$DESTDIR/$NAUTILUS_SKEL_TARGET/Unball" ]; then
		echo "Installing Nautilus script links."
		mkdir -p "$DESTDIR/$NAUTILUS_SKEL_TARGET"
		ln -s "$UNBALL_TARGET" "$DESTDIR/$NAUTILUS_SKEL_TARGET/Unball"
		ln -s "$MOVETOZIP_TARGET" "$DESTDIR/$NAUTILUS_SKEL_TARGET/Move to ZIP"
		user_enum install_nautilus
	fi
fi
