Unball
======
by deitarion (Stephan Sokolow)
Version 0.2.99.0

Inspired by [maitre's unball](http://kde-look.org/content/show.php/KDE+Unballer?content=12561)
(It would be based on it, but there was none of the old code left by the time I was done the first release)

.. image:: https://travis-ci.org/ssokolow/unball.png
   :target: https://travis-ci.org/ssokolow/unball

Version 1.0.0 of this script will be released when I am satisfied that the interface behaviour has stabilized
and that the list of supported archive formats and planned features have grown/shrunk enough.

Known Flaws
-----------

- As of 2013-03-28, the Python port is functional with the remaining test failures caused by incomplete
  support for certain formats already supported by the old shell script version.
- **Installation for unball 0.3.x is still being converted from ``install.sh`` to ``setup.py``.**
- The style and architecture for the codebase and test suite are still very much stuck back in 2009.
- Documentation is still catching up to the 0.3.x rewrite.
- Gentoo's app-arch/unarj isn't supported because app-arch/arj is GPLed and better in every way.

Requirements:
-------------

Base Dependencies:

- A POSIX-compliant system (Linux, \*BSD, MacOS X, etc.)
- Python 2.6+ (3.x support not yet ready)

For unball:

- The extraction tools for the formats you use, accessible via the ``PATH``.

For moveToZip:

- InfoZIP (The ``zip`` command) is non-optional.

For the unit tests:

- As many of the supported extraction tools as possible

For the Xfce integration:

- A version of Xfce which uses Thunar as it's file manager
- Zenity (for the "Extract to..." option)

Installation:
-------------

**TODO**

Usage:
------

Console
  Just run ``unball someArchive.zip`` and let it do it's thing.
  For details, run ``unball --help``.

KDE

  - Right-click any archive and "Extract with unball" will be available in the Actions menu.
  - Right-click any folder and "Move to Zip Archive" will be available in the Actions menu.

GNOME

  - Right-click any archive and "Unball" will be available in the Scripts menu.
  - Right-click any file or folder and "Move to ZIP" will be available in the Scripts menu.

Xfce
  thunar-archive-plugin will offer unball (and moveToZip) as the backend for it's archive functions.

The unit tests can be run by typing ``./run_test.py`` after installing unball. (preferrably not as root)
For details on the options ``run_test.py`` accepts, use the ``--help`` option.

Tips:
-----

When using Konqueror, you can easily batch-convert a collection of assorted archives to Zips:

1. Select all of the archives and choose "Extract with unball" from the Actions menu.
2. Select all of the folders which result and choose "Move to Zip Archive" from the Actions menu.
3. Once all the folders are gone, delete the original non-Zip archives.
   (The folders will only vanish after the zip archives have been tested)

I haven't had a chance to check whether this works in Nautilus yet, but it should.

To convert a WinHTTrack-generated library of saved websites into zips for easy archival on CDs or DVDs:

1. CD into the folder where your library is kept
2. Run this command --> ``for SITE in *.whtt; do moveToZip.sh "${SITE%.whtt}"; rm -f "$SITE"; done``

