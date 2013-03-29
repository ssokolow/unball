#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unball 0.2.99.0
Copyright 2005-2009, 2013 Stephan Sokolow

See the README file in the distribution archive for details.
If unball came pre-installed, the README can be viewed at
https://github.com/ssokolow/unball

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

--snip--
@todo: Add a command-line option for forcing the archive's name on the
       generated directory.
@todo: Re-implement the "Found <filetype>, unballing <path>" message.
@todo: Decide how to implement --overwrite and --verbose
@todo: Do the exception handling in a way which produces nicer output.
@todo: Consider switching to the logging module for error messages.
@todo: Now that this is in Python, restructure the code so it provides a proper
       API for being imported by other Python programs.
@todo: Verify that POSIX signals don't circumvent try/finally. Handle them if
       necessary.
@todo: Consider re-adding the convenience identifiers for skipped files in
       --verbose mode.
"""

__appname__ = "Unball"
__author__  = "Stephan Sokolow (deitarion/SSokolow)"
__version__ = "0.2.99.0"
__license__ = "GNU GPL 2.0 or later"

RECURSION_LIMIT = 5  #: Controls the anti-quine check.

import errno, os, subprocess, sys
from stat import S_IRUSR, S_IXUSR

from .mimetypes import pathToMimetype
from .extractors import (mimeToExtractor,
                        NoExtractorError, UnsupportedFiletypeError)
from .util import TempTarget

# TODO: See if I can refactor to remove the need for this
from .extractors import EXTRACTORS

class UnballError(Exception):
    """Base class for all Unball-internal exceptions."""
class NothingProducedError(UnballError):
    """The extractor (usually a subprocess) didn't return an error condition
    but also didn't extract anything."""

def tryExtract(srcFile, targetDir=None, level=0):
    """Attempt to extract the given archive.

    @param srcFile: The potential archive file for which an extraction attempt
        should be made.
    @param targetDir: The directory in which the containing folder for the
        contents should appear. (Use C{None} for "same as source file")
    @param level: Recursion level. Used to protect the nested
        extractor/decompressor from quines. (Proven possible in zipfiles.
        I don't know about others.)
    @type srcFile: C{str} | C{unicode}
    @type targetDir: C{str} | C{unicode}
    @type level: C{int}

    @return: The path to the extracted content.
    @rtype: C{str}

    @raises IOError: The source or target are invalid or require additional
    permissions.
    @raises OSError: The specified target isn't a directory or already
    contains the file/directory name extraction produced.
    @raises CalledProcessError: The subprocess called by an L{Extractor}
    instance returned a non-zero exit code.
    @raises NoExtractorError: The mimetype of the given filetype is
    supported but no viable extractors were found.
    @raises NothingProducedError: The L{Extractor} exited cleanly but no
    files or directories were extracted. (eg. unace when it fails)
    @raises UnsupportedFiletypeError: The mimetype of the given file has no
    L{Extractor} mappings.
    """

    srcFile = os.path.abspath(srcFile)
    targetDir = os.path.abspath(targetDir or os.path.dirname(srcFile))

    # Minimize the chance for ambiguous error messages from subprocesses.
    if not os.path.exists(srcFile):
        raise IOError(errno.ENOENT, "Source file does not exist", srcFile)
    elif os.path.isdir(srcFile):
        raise IOError(errno.EISDIR, "Source file is a directory", srcFile)
    elif not os.access(srcFile, os.R_OK):
        raise IOError(errno.EACCES, "Access denied to source file", srcFile)

    # Check for viable extractors for the given file
    mime = pathToMimetype(srcFile, EXTRACTORS)
    extractors = mimeToExtractor(mime)

    prefer_contained_name = True  # TODO: Make this configurable

    # TODO: Unit test for proper output folder name generation
    # TODO: Make sure there's always a test file which LACKS a containing
    # folder for the files within.
    target_name = os.path.splitext(os.path.basename(srcFile))[0]
    context = TempTarget(os.path.join(targetDir, target_name),
                         prefix='unball-', parent=targetDir, collapse=True)

    with context as tempTarget:
        extractors[0](srcFile, tempTarget)  # Raises exception on non-zero exit

        # Ensure that unball can't create files and dirs with 000 permissions.
        for fldr, dirs, files in os.walk(tempTarget):
            for dirname in dirs:
                path = os.path.join(fldr, dirname)
                os.chmod(path, os.stat(path).st_mode | S_IRUSR | S_IXUSR)
            for filename in files:
                path = os.path.join(fldr, filename)
                os.chmod(path, os.stat(path).st_mode | S_IRUSR)

        contents = os.listdir(tempTarget)
        first_contained = os.path.join(tempTarget, contents[0])
        if len(contents) == 0:
            raise NothingProducedError("Operation completed but temp "
                "folder is empty for %s" % context.target)
        elif (len(contents) == 1 and level < RECURSION_LIMIT and
                os.path.isfile(first_contained)):
                # Handle nesting like .tar.7z
            #TODO: Should I go as far as explicitly collapsing nested
            #      containing folders?
            try:
                tryExtract(first_contained, None, level + 1)
            except UnsupportedFiletypeError:
                pass
            else:
                os.remove(first_contained)

        # TODO: Unit test that nested extraction doesn't break this
        contents = os.listdir(tempTarget)
        if len(contents) == 1 and prefer_contained_name:
            context.target = os.path.join(
                    os.path.dirname(context.target), contents[0])

        #@param prefer_contained_name: If this and L{collapse} are C{True} and
        #  only one file/folder exists in the temporary folder on L{__exit__},
        #  preserve its name by replacing the last path component of L{target}
        #  before the rename operation.

        # If the input file is extensionless and --samedir is set.
        # (Or the input file contains a single file of the same name
        # and it's either a non-archive, corrupt, or the recursion
        # limit for catching archive-based quines was reached)
        # XXX: How is this relevant to the recursion limit again?
        if srcFile == context.target:
            context.target = context.target + '.out'

    return context.target


def self_test(silent=False):
    """Verify the integrity of the internal mapping tables.
    @todo: Clean up this code."""
    #XXX: Move self-testing to a separate module?
    from extractors import Extractor, EXTRACTORS, FALLBACK_DESCRIPTIONS

    OK = True

    # Check for FALLBACK_DESCRIPTIONS messages which will never be used
    mixed_messages = [x for x in EXTRACTORS if x in FALLBACK_DESCRIPTIONS]
    if mixed_messages:
        OK = False
        if not silent:
            print("\nEXTRACTORS currently overrides FALLBACK_DESCRIPTIONS. "
                  "Mimetypes should only appear in one:")
            print('\n'.join(mixed_messages))

    untestables = []
    for mimetype in sorted(EXTRACTORS):
        extractor = EXTRACTORS[mimetype]
        if isinstance(extractor, Extractor):
            if extractor.isViable():
                continue
        else:
            if any(x.isViable() for x in extractor):
                continue
        untestables.append(mimetype)

    if untestables and not silent:
        print("\nNo viable extractors found for the following mimetypes:")
        print('\n'.join(untestables))

    return OK

def get_opt_parser():
    """Build and return an OptionParser instance for unball."""
    from optparse import OptionParser

    descr = ("Extract one or more archives, given only the filename, while " +
             "ensuring they won't make a mess.")

    parser = OptionParser(usage="%prog [options] archive ...",
                        description=descr,
                        version="%%prog %s" % __version__)
    parser.add_option('-v', '--verbose', action="count", dest="verbose",
        default=0, help="Increase verbosity")
    parser.add_option('-d', '--dir', action="store", dest="outdir",
        metavar="DIR", default=os.getcwdu(), help="Set the target directory")
    parser.add_option('-D', '--samedir', action="store_false", dest="outdir",
        help="Extract to the directory containing the source file (default is "
        "the current working directory)")
    parser.add_option('--strict', action="store_true", dest="strict_return",
        help="Don't return success unless all input files were archives.")
    parser.add_option("--self-test", action="store_true", dest="self_test",
        help="Test the referential integrity of the filetype lookup tables.")

    return parser

def main_func():
    parser = get_opt_parser()
    opts, args = parser.parse_args()

    if opts.self_test:
        if self_test():
            print("\nNo inconsistencies found")
        parser.exit()

    if not len(args):
        parser.print_help()
        parser.exit(errno.ENOENT)  # Apparently it's standard to use ENOENT.

    if opts.outdir and not os.access(opts.outdir, os.W_OK):
        print("FATAL: No write permissions for given destination directory")
        parser.exit(errno.EPERM)

    failures, cautions = [], []
    last_errcode = 0
    for archive in args:
        try:
            print("Extracted to %s" % tryExtract(archive, opts.outdir))
            #TODO: Do this in a way which produces nicer output.
        except UnsupportedFiletypeError as err:
            cautions.append(archive)
        except NothingProducedError as err:  # Bug trap triggered
            failures.append(str(err))
            last_errcode = 1
        except IOError as err:  # Permissions error
            failures.append(str(err))
            last_errcode = 2
        except OSError as err:  # Path error (eg. target exists or not a dir)
            failures.append(str(err))
            last_errcode = 3
        except NoExtractorError as err:  # Could not find suitable extractor
            failures.append(str(err))
            last_errcode = 4
        except subprocess.CalledProcessError as err:  # Extractor failed
            if err.returncode >= 0:
                failures.append(str(err))
                last_errcode = 5
            else:
                last_errcode = 6
                break
        except Exception as err:   # Unknown error
            failures.append(str(err))
            last_errcode = 7

    if failures:
        print('')
        print("Unball encountered errors while extracting one or more files:")
        print('\t' + '\n\t'.join(failures))
        print('')
        raise

    if cautions:
        print("One or more provided files were not recognized as archives. ")
        print("If you are certain they are, please file a bug at " +
              "http://launchpad.net/unball so support can be added.")
        print(' - ' + '\n - '.join(cautions))

    if failures or (cautions and opts.strict_return):
        sys.exit(last_errcode or 1)

if __name__ == '__main__':
    main_func()
