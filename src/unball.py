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
@todo: Use the following to set up an internal header matcher:
    - http://www.fileformat.info/format/arc/corion.htm
    - http://www.fileformat.info/format/zoo/corion.htm
@todo: Add a command-line option for forcing the archive's name on the
       generated directory.
@todo: Re-implement the "Found <filetype>, unballing <path>" message.
@todo: Decide how to implement --overwrite and --verbose
@todo: Do the exception handling in a way which produces nicer output.
@todo: Consider switching to the logging module for error messages.
@todo: Will unstuff and cabextract handle self-extracting cabs?
       (If so, add application/cab to the .exe list)
@todo: Fix this so it handles "one ext to multiple mimetypes" mappings properly
@todo: Now that this is in Python, restructure the code so it provides a proper
       API for being imported by other Python programs.
@todo: Add password-protected archive tests to ensure subprocesses don't pause
       to ask for a password.
@todo: Verify that POSIX signals don't circumvent try/finally. Handle them if
       necessary.
@todo: Add tests for non-StuffIt MacBinary files.
@todo: Consider re-adding the convenience identifiers for skipped files in
       --verbose mode.
@todo: Add a BlakHole test archive and figure out a way to reliably identify
       extractors that aren't getting tested, not just extensions.
@todo: Look into what unshar and unmakeself actually do. I may need to relegate
       them to a --use-unsafe-extractors flag.
@todo: Figure out a better syntax for specifying extractor arguments.
       (especially destination directories)

@todo: The extension checker needs to be rewritten to support this
(Oh, and what does compress.exe do with an extension longer than 3 characters?)
 - *.??_) extract extract_gbzip msexpand "$FILE" "Microsoft compress.exe-packed file";;

@todo: Un-handled archive formats:
 - atr, bzf, cpt, dar, dmg, dz, gcf, kgb, partimg, pit, pq6, qda, rk, sfpack,
   umod, uz2, zz

@todo: CD/DVD images which should probably trigger some kind of message telling
the user how to mount them or convert them so they can be burned:
ccd, cue, nrg, bwi, b5i, mdf, uif, daa


@todo: Stuff to peruse for new formats as I find the time:
 - http://en.wikipedia.org/wiki/List_of_archive_formats
 - http://en.wikipedia.org/wiki/Comparison_of_archive_formats
 - http://www.maximumcompression.com/index.html
 - http://www.squeezechart.com/
 - http://blackfox.wz.cz/pcman/benchmark.htm
 - http://www.cs.fit.edu/~mmahoney/compression/
"""

__appname__ = "Unball"
__author__  = "Stephan Sokolow (deitarion/SSokolow)"
__version__ = "0.2.99.0"
__license__ = "GNU GPL 2.0 or later"

RECURSION_LIMIT = 5  #: Controls the anti-quine check.

import errno, os, subprocess, shutil, sys, tempfile
from stat import S_IRUSR, S_IXUSR

try:
    import magic
    mime_checker = magic.open(magic.MAGIC_MIME)
    mime_checker.load()

    def headerToMimetype(path, checker=mime_checker.file):
        """Given a path, attempt to determine the file's mimetype by examining
        the file's contents.

        @param checker: Ignore this. Only present if "import magic" succeeded.
        @param path: The path to the file to be inspected.
        @type path: C{str}

        @return: Mimetype of the file or application/octet-stream on failure.
        @rtype: C{str}
        @raises IOError: The file does not exist or cannot be read.

        @todo: Polish this code and copy it to nonstdlib.
        """
        if not os.path.exists(path):
            raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        elif not os.access(path, os.R_OK):
            raise IOError(errno.EACCES, os.strerror(errno.EACCES), path)
        else:
            mime = checker(path).decode('string_escape').split()[0]

            # TODO: Unit test this. IF nothing else, ';' is needed for
            # arctest.header on Ubuntu 12.04 LTS.
            mime = mime.rstrip(',;')
            return mime

    del mime_checker
except ImportError:  # TODO: Can magic.open or mime_checker.load() fail?
    def headerToMimetype(path):
        """Given a path, attempt to determine the file's mimetype by examining
        the file's contents.

        @param path: The path to the file to be inspected.
        @type path: C{str}
        @return: Mimetype of the file or application/octet-stream on failure.
        @rtype: C{str}

        @todo: When can the C{file} command return non-zero error codes?
        @todo: Polish this code and copy it to nonstdlib.
        """
        # TODO: Implement a completely internal version of this.
        # (And implement detection of COMPRESS.EXE files
        #  http://www.cabextract.org.uk/libmspack/doc/szdd_kwaj_format.html)

        _sp, _cmd = subprocess, ['file', '-bi', path]
        try:
            mime = _sp.Popen(_cmd, stdout=_sp.PIPE).stdout.read().strip()
            mime = mime.decode('string_escape').split()[0].rstrip(',')
        except OSError:
            mime = 'application/octet-stream'
        return mime

class UnballError(Exception):
    """Base class for all Unball-internal exceptions."""
class NoExtractorError(UnballError):
    """Raised when no viable extractor can be found for a supported mimetype"""
class NothingProducedError(UnballError):
    """The extractor (usually a subprocess) didn't return an error condition
    but also didn't extract anything."""
class UnsupportedFiletypeError(UnballError):
    """Raised when the given mimetype is completely unsupported regardless of
    conditions."""

class BinYes(object):
    """A file-like object mimicking /bin/yes to be passed to stdin so
    broken commands like unace don't hang."""
    @staticmethod
    def read(*args):
        return "y\n"

    @staticmethod
    def fileno():
        return None

class Extractor(object):
    """A generic wrapper for calling external extractor tools which behave
    in a reasonably sane manner and don't attempt to delete the source file on
    success."""
    def __init__(self, *base_args):
        """Store the provided commandline for extracting archives."""
        self._args = list(base_args)

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__,
                ', '.join(repr(x) for x in getattr(self, '_args', [])))

    def __call__(self, path, target):
        """Use the command provided in the constructor to extract the given
        archive to the given destination directory.

        @param path: The archive to be extracted.
        @param target: The directory into which the extracted files should be
        placed.
        @type path: C{str}
        @type target: C{str}
        """

        if False:  # --verbose test goes here
            _out = None
            _err = None
        else:
            _out = open(os.devnull, 'w')
            _err = subprocess.STDOUT

        # Can't redirect on Windows if the FDs are closed.
        _fds = (os.name != 'nt')

        # (The cwd= of this was the other major portion of the shell script)
        subprocess.check_call(self._args + [path], stdin=BinYes,
                    stdout=_out, stderr=_err, close_fds=_fds,
                    cwd=target, universal_newlines=True)

    def isViable(self):
        """Check to see if the extractor binary can be found in the PATH."""
        return bool(which(self._args[0]))

class NamedOutputExtractor(Extractor):
    """A wrapper class for extractors which don't generate their own output
    filename and require one be provided.

    Behaviour of src_ext and target_ext:
     - C{path=foo.gz , src_ext=.gz , target_ext=None: foo}
     - C{path=foo.gz , src_ext=.gz , target_ext=.txt: foo.txt}
     - C{path=foo.goz, src_ext=.gz , target_ext=.out: foo.goz.out}
     - C{path=foo.lol, src_ext=None, target_ext=.wut: foo.lol.wut}
     """
    def __init__(self, args, src_ext=None, target_ext=None,
                 outfile_option=None):
        """
        @param src_ext: An extension to strip from the target path if found.
        @param target_ext: An extension to add to the target path.
        @param outfile_option: If present, the command-line option with which
            to prefix the output filename. Whether or not it ends with a space
            is significant.
        @type src_ext: C{str}
        @type target_ext: C{str}
        @type outfile_option: C{str}

        @raises SyntaxError: You failed to provide at least one of src_ext or
            target_ext
        """
        if isinstance(args, basestring):
            args = [args]
        Extractor.__init__(self, *args)
        if not (src_ext or target_ext):
            raise SyntaxError("NamedOutputExtractor requires at least one of "
                              "src_ext and target_ext")
        self.src_ext = src_ext
        self.target_ext = target_ext
        self.outfile_option = outfile_option

    def __call__(self, path, target):
        """Use the command provided in the constructor to extract the given
        archive to the given destination directory.

        @param path: The archive to be extracted.
        @param target: The directory into which the extracted files should be
        placed.
        @type path: C{str}
        @type target: C{str}
        """

        if False:  # --verbose test goes here
            _out = None
            _err = None
        else:
            _out = open(os.devnull, 'w')
            _err = subprocess.STDOUT

        # Can't redirect on Windows if the FDs are closed.
        _fds = (os.name != 'nt')

        _outname = self._make_target_filename(path, target, self.src_ext,
                                              self.target_ext)
        args = [path]

        if self.outfile_option:
            if self.outfile_option.endswith(' '):
                args.extend([self.outfile_option.strip(), _outname])
            else:
                args.append(self.outfile_option.strip() + _outname)
        else:
            args.append(_outname)

        # (The cwd= of this was the other major portion of the shell script)
        subprocess.check_call(self._args + args, stdin=BinYes,
                    stdout=_out, stderr=_err, close_fds=_fds,
                    cwd=target, universal_newlines=True)

    def _make_target_filename(self, srcPath, destDir, srcExt=None, destExt=None):
        """A pseudo-protected function for generating a target filename when
        wrapping an extractor that does not provide one on its own.

        @param srcExt: an extension to be stripped if found on srcPath.
        @param destExt: an extension to be added.
        @type srcExt: C{str} or iterable of C{str}s.
        @type destExt: C{str}

        @returns: The target filename
        @rtype: C{str}

        @note: If, after other transformations, C{srcPath == target_path}, then
        C{.out} will be appended.
        """
        target_path = os.path.join(destDir, os.path.split(srcPath)[1])
        if srcExt:
            if isinstance(srcExt, basestring):
                srcExt = (srcExt,)
            for ext in srcExt:
                if target_path.lower().endswith(ext):
                    target_path = target_path[:-len(ext)]
                    break
        if destExt:
            target_path += destExt
        if target_path == srcPath:
            target_path += '.out'
        return target_path

class PipeExtractor(NamedOutputExtractor):
    """A wrapper class for extractors which delete the source file on success
    unless asked to pipe the output to stdout.

    @note: C{outfile_option} is ignored.
    """
    CHUNK_SIZE = 4096  #: Provided for subclasses which do their own C{read}ing

    def __call__(self, path, target):
        target_path = self._make_target_filename(path, target, self.src_ext,
                                                 self.target_ext)
        _out = open(target_path, 'wb')

        if False:  # --verbose test goes here
            _err = None
        else:
            _err = open(os.devnull, 'w')

        # Can't redirect on Windows if the FDs are closed.
        _fds = (os.name != 'nt')

        # (The cwd= of this was the other major portion of the shell script)
        subprocess.check_call(self._args, stdin=open(path, 'rb'),
                    stdout=_out, stderr=_err, close_fds=_fds, cwd=target,
                    universal_newlines=False)

class ZipExtractor(Extractor):
    """An internal fallback extractor for zip archives.
    Only understands the most common subset of zip file types."""
    def __init__(self):
        """no-op"""
    def __call__(self, path, target):
        """Extract C{path} into C{target} using the C{zipfile} module.

        @note: No need to use C{zipfile.is_zipfile} because we want an
        exception on failure anyway.

        @todo: Write a fallback implementation.
        C{ZipFile.extractall} was added in Python 2.6
        """
        import zipfile
        if getattr(zipfile.ZipFile, 'extractall', None):
            zipfile.ZipFile(path, 'r').extractall(target)
        else:
            raise NotImplementedError("Fallback zip extraction currently " +
                    "requires Python 2.6 or higher for ZipFile.extractall")

    def isViable(self):
        """Check to see if Python stdlib was built with zipfile support."""
        try:
            import zipfile
            zipfile  # Silence flake8 complaint about unused import
            return True
        except ImportError:
            return False

class TarExtractor(Extractor):
    """An internal fallback extractor for tar archives.
    Probably doesn't understand everything GNU Tar can but it does
    transparently support gzip and bzip2 compression if Python stdlib does."""
    def __init__(self):
        """no-op"""
        pass

    def __call__(self, path, target):
        """Extract C{path} into C{target} using the C{zipfile} module.

        @note: No need to use C{tarfile.is_tarfile} because we want an
        exception on failure anyway."""
        import tarfile
        tarfile.open(path, 'r').extractall(target)

    def isViable(self):
        """Check to see if Python stdlib was built with tarfile support."""
        try:
            import tarfile
            tarfile  # Silence flake8 complaint about unused import
            return True
        except ImportError:
            return False

class GZipExtractor(PipeExtractor):
    """An internal fallback extractor for gzip-compressed files."""
    def __init__(self):
        """no-op"""
    def __call__(self, path, target):
        """Decompress C{path} into C{target} using the C{gzip} module."""
        import gzip
        target_path = self._make_target_filename(path, target, '.gz')
        in_handle, out_handle = gzip.open(path), open(target_path, 'wb')
        for block in iter(lambda: in_handle.read(self.CHUNK_SIZE), ''):
            out_handle.write(block)
        in_handle.close()
        out_handle.close()

    def isViable(self):
        """Check to see if Python stdlib was built with gzip support."""
        try:
            import gzip
            gzip  # Silence flake8 complaint about unused import
            return True
        except ImportError:
            return False

class BZip2Extractor(PipeExtractor):
    """An internal fallback extractor for bzip2-compressed files."""
    def __init__(self):
        """no-op"""
    def __call__(self, path, target):
        """Decompress C{path} into C{target} using the C{bz2} module."""
        import bz2
        target_path = self._make_target_filename(path, target, '.bz2')
        in_handle, out_handle = bz2.BZ2File(path, 'r'), open(target_path, 'wb')
        for block in iter(lambda: in_handle.read(self.CHUNK_SIZE), ''):
            out_handle.write(block)
        in_handle.close()
        out_handle.close()

    def isViable(self):
        """Check to see if Python stdlib was built with bzip2 support."""
        try:
            import bz2
            bz2  # Silence flake8 complaint about unused import
            return True
        except ImportError:
            return False

class UUDecoder(Extractor):
    """An internal fallback extractor for uuencoded files."""
    def __init__(self):
        """no-op"""
    def __call__(self, path, target):
        """Decode C{path} into C{target} using the C{uu} module.
        @todo: Confirm that this will always extract within C{target}"""
        import uu
        cwd = os.getcwd()
        try:
            os.chdir(target)
            uu.decode(file(path, 'rb'))
        finally:
            os.chdir(cwd)

    def isViable(self):
        """Check to see if Python stdlib was built with uudecode support."""
        try:
            import uu
            uu  # Silence flake8 complaint about unused import
            return True
        except ImportError:
            return False

class B64Decoder(NamedOutputExtractor):
    """An internal fallback extractor for base64-encoded files."""
    def __init__(self):
        """@todo: Rework this so it doesn't hard-code the extensions. (DRY)"""
        NamedOutputExtractor.__init__(self, [], ('.b64', '.mim'))

    def __call__(self, path, target):
        """Decode C{path} into C{target} using the C{base64} module."""
        import base64
        cwd = os.getcwd()
        out = self._make_target_filename(path, target, self.src_ext)
        try:
            os.chdir(target)
            base64.decode(path, out)
        finally:
            os.chdir(cwd)

    def isViable(self):
        """Check to see if Python stdlib was built with base64 support."""
        try:
            import base64
            base64  # Silence flake8 complaint about unused import
            return True
        except ImportError:
            return False

class BinhexDecoder(Extractor):
    """An internal fallback extractor for binhex-encoded files."""
    def __init__(self):
        """no-op"""
    def __call__(self, path, target):
        """Decode C{path} into C{target} using the C{binhex} module.
        @todo: Confirm that this will always extract within C{target}"""
        import binhex
        cwd = os.getcwd()
        try:
            os.chdir(target)
            binhex.hexbin(path)
        finally:
            os.chdir(cwd)

    def isViable(self):
        """Check to see if Python stdlib was built with binhex support."""
        try:
            import binhex
            binhex  # Silence flake8 complaint about unused import
            return True
        except ImportError:
            return False

class SitExtractor(Extractor):
    """A wrapper class for hiding the common oddities involved in calling
    unstuff as a subprocess."""
    def __init__(self, prefix='/opt/stuffit/bin'):
        """Store the provided path or iterable of paths to be appended to the
        executable search path used when calling the extractor.
        @param prefix: A path or iterable of paths to search for unstuff.
        @type prefix: C{str}|C{tuple}|C{list}|...
        """
        self.prefixes = isinstance(prefix, basestring) and [prefix] or prefix

        path = os.environ.get('PATH', os.defpath).split(os.pathsep)
        self.path = os.pathsep.join(path + self.prefixes)

    def __call__(self, path, target):
        """Use unstuff to extract the given Stuffit archive.
        @note: If I read my old shell script correctly, unstuff only accepts
        relative paths and that's why I break from the convention of not
        relying on the working directory being correctly set.

        @param path: The archive to be extracted.
        @param target: The directory into which the extracted files should be
        placed.
        @type path: C{str}
        @type target: C{str}
        """
        if False:  # --verbose test goes here
            _out = None
            _err = None
        else:
            _out = open(os.devnull, 'w')
            _err = subprocess.STDOUT

        # Can't redirect on Windows if the FDs are closed.
        _fds = (os.name != 'nt')

        # Make finding unstuff as flexible as possible
        _env = os.environ.copy()
        _env['PATH'] = self.path

        # unstuff only accepts relative paths
        if getattr(os.path, 'relpath', None):
            path = os.path.relpath(path, target)
        else:
            # os.path.relpath was only added in Python 2.6
            path = path.lstrip(os.sep).lstrip(os.altsep or os.sep)
            for i in range(os.path.normpath(target).count(os.sep)):
                path = os.path.join(os.pardir, path)

        # (The cwd= of this was the other major portion of the shell script)
        subprocess.check_call(['unstuff', '--destination=.', path],
                    stdin=BinYes, stdout=_out, stderr=_err,
                    close_fds=_fds, cwd=target, env=_env,
                    universal_newlines=True)

    def isViable(self):
        """Check to see if the PATH plus the given addition provides unstuff"""
        return bool(which('unstuff', self.path))

class TryAll(Extractor):
    """A meta-extractor for trying several other extractors until one works.
    Used for situations where it's not feasible to detect by extension or
    header. (eg. self-extracting arctives)
    """
    def __init__(self, *mimes):
        """Takes a list of mimetypes to be lazily resolved to extractors.
        @note: Order is significant."""
        self.mimes = mimes
        self.extractors = []

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                ', '.join(repr(x) for x in self.mimes))

    def __call__(self, path, target):
        """Attempt to decompress C{path} to C{target} using one of the given
        extractors."""
        self.isViable()  # Make sure self.extractors has been built.

        if not self.extractors:
            raise NoExtractorError("No extractors for file: %s" % path)

        for potential_extractor in self.extractors:
            try:
                before = len(os.listdir(target))
                potential_extractor(path, target)
                after = len(os.listdir(target))

                if before < after:
                    return  # Success
            except subprocess.CalledProcessError:
                pass  # Better luck next time?

    def isViable(self):
        """Check whether any of the sub-extractors are viable.
        @note: Also triggers lazy-loading of the extractors list."""
        if self.extractors:
            return True

        self.extractors = []
        for mime in self.mimes:
            if isinstance(mime, Extractor):
                if mime.isViable():
                    self.extractors.append(mime)
                continue
            potentials = mimeToExtractor(mime)
            if potentials and potentials[0].isViable():
                self.extractors.append(potentials[0])

        return bool(self.extractors)

EXTRACTORS = {
        'application/x-7z-compressed'  : (Extractor('7z', 'x'),
                                          Extractor('7za', 'x'),
                                          Extractor('7zr', 'x'),
                                          Extractor('sqc', 'x')),
        'application/x-ace-compressed' : (Extractor('unace-bin', 'x', '-y'),
                                          Extractor('unace', 'x', '-y'),
                                          Extractor('sqc', 'x')),
        'application/x-adf'            : (Extractor('unadf'),
                                          Extractor('readdisk'),
                                          Extractor('e-readdisk')),
        'application/x-adz'            :  PipeExtractor('gunzip', '.adz', '.adf'),
        'application/x-alz'            :  Extractor('unalz'),
        'application/x-ar'             :  Extractor('ar', 'x'),
        'application/x-arc'            :  Extractor('arc', 'x'),
        'application/arj'              : (Extractor('arj', 'x', '-y'),
                                          Extractor('unarj', 'x'),
                                          Extractor('sqc', 'x')),
        'application/bzip2'            : (PipeExtractor('bunzip2', '.bz2'),
                                          BZip2Extractor()),
        'application/cab'              : TryAll(Extractor('cabextract'),
                                          Extractor('unshield'),
                                          Extractor('sqc', 'x')),
        'application/x-compress'       : (PipeExtractor('uncompress.real', '.z'),
                                          PipeExtractor('uncompress', '.z')),
        'application/x-cpio'           :  Extractor('cpio', '--force-local', '--quiet', '-idI'),
        'application/x-deb'            :  Extractor('ar', 'x'),
        'application/x-dosexec'        :  [],    # See below for how this works
        'application/x-diskmasher'     : (Extractor('xdms', 'u'),
                                          NamedOutputExtractor('undms', '.dms', '.adf')),
        'application/x-gzip'           :  (PipeExtractor('gunzip', '.gz'),
                                           GZipExtractor()),
        'application/lzh'              : (Extractor('lha', 'x'),
                                          Extractor('sqc', 'x')),
        'application/lzx'              :  Extractor('unlzx', '-x'),
        'application/x-lzop'           :  Extractor('lzop', '-x',),
        'application/macbinary'        : (SitExtractor(),
                                          Extractor('macunpack', '-f')),
        'application/mac-binhex40'     : (SitExtractor(),
                                          Extractor('uudeview', '-i')),
        'application/mime'             :  Extractor('uudeview', '-ib'),
        'application/msi'              :  Extractor('7z', 'x'),
        'application/x-rar'            : (Extractor('unrar', 'x', '-y', '-p-'),
                                          Extractor('rar', 'x', '-y', '-p-'),
                                          Extractor('sqc', 'x')),
        'application/x-rpm'            : (Extractor('rpm2cpio'),
                                          Extractor('rpm2targz')),
        'application/x-rzip'           :  NamedOutputExtractor(['runzip', '-k'], '.rz', outfile_option='-o '),
        'application/x-extension-sfark':  Extractor('sfarkxtc'),
        'application/x-shar'           : TryAll(Extractor('unmakeself'),
                                          Extractor('unshar')),
        'application/x-slp'            :  Extractor('alien', '-g'),  # Untested for lack of a .slp file
        'application/x-squeeze'        :  Extractor('sqc', 'x'),
        'application/x-stuffit'        :  SitExtractor(),
        'application/x-tar'            : (Extractor('tar', 'xf'),
                                          TarExtractor()),
        'application/x-uuencode'       : (Extractor('uudeview', '-i'),
                                          Extractor('uudecode'),
                                          UUDecoder()),
        'application/x-xar'            :  Extractor('xar', '-xf'),
        'application/x-xx-encoded'     : (Extractor('uudeview', '-i'),
                                          Extractor('xxdecode')),
        'application/x-yenc-encoded'   : (Extractor('uudeview', '-i'),
                                          Extractor('ydecode'),
                                          Extractor('yydecode')),
        'application/zip'              : (Extractor('7z', 'x'),
                                          Extractor('7za', 'x'),
                                          Extractor('unzip', '-q'),
                                          ZipExtractor(),
                                          Extractor('jar', 'xf'),
                                          Extractor('sqc', 'x')),
        'application/x-zoo'            : (Extractor('unzoo', '-x'),
                                          Extractor('zoo', '-extract'))
}
"""Mappings from mimetypes to Extractor instances or iterables thereof.
@note: Order is significant within the target iterables."""

# Dynamically build the extraction trial sequence for self-extractors from the
# sequences for possible self-extractor formats.
EXTRACTORS['application/x-dosexec'] = TryAll(
            'application/zip',
            'application/x-rar',
            'application/arj',
            'application/x-7z-compressed',
            'application/lzh',
            'application/x-ace-compressed')

aliases = {
        'application/x-archive'             : 'application/x-ar',
        'application/x-ace'                 : 'application/x-ace-compressed',
        'application/x-arj'                 : 'application/arj',
        'application/x-bcpio'               : 'application/x-cpio',
        'application/x-bz2'                 : 'application/bzip2',
        'application/x-bzip'                : 'application/bzip2',
        'application/x-bzip2'               : 'application/bzip2',
        'application/x-compressed'          : 'application/x-gzip',
        'application/x-dms'                 : 'application/x-diskmasher',
        'application/x-gtar'                : 'application/x-tar',
        'application/java-archive'          : 'application/zip',
        'application/x-lha'                 : 'application/lzh',
        'application/x-lharc'               : 'application/lzh',
        'application/x-lzh'                 : 'application/lzh',
        'application/x-lzh-archive'         : 'application/lzh',
        'application/x-lzx'                 : 'application/lzx',
        'application/x-ole-storage'         : 'application/msi',
        'application/x-macbinary'           : 'application/macbinary',
        'application/x-mime-encoded'        : 'application/mime',
        'application/x-msi'                 : 'application/msi',
        'application/x-msiexec'             : 'application/msi',
        'application/sea'                   : 'application/x-stuffit',
        'application/x-sea'                 : 'application/x-stuffit',
        'application/x-sh'                  : 'application/x-shar',
        'application/stuffit-lite'          : 'application/x-stuffit',
        'application/x-sv4cpio'             : 'application/x-cpio',
        'application/vnd.ms-cab-compressed' : 'application/cab',
        'application/x-webarchive'          : 'application/x-tar',
        'application/x-xpinstall'           : 'application/zip',
        'application/x-zip'                 : 'application/zip',
        'x-compress'                        : 'application/x-compress',
        'x-gzip'                            : 'application/x-gzip',
        'x-uuencode'                        : 'application/x-uuencode',
}
for key in aliases:
    if key in EXTRACTORS:
        raise Exception("OVERWRITE: %s -> %s" % (aliases[key], key))
    EXTRACTORS[key] = EXTRACTORS[aliases[key]]
del aliases, key

EXTENSIONS = {
        '.7z'   : 'application/x-7z-compressed',
        '.a'    : 'application/x-ar',
        '.ace'  : 'application/x-ace-compressed',
        '.adf'  : 'application/x-adf',
        '.adz'  : 'application/x-adz',
        '.alz'  : 'application/x-alz',
        '.ar'   : 'application/x-ar',
        '.arc'  : 'application/x-arc',
        '.arj'  : 'application/arj',
        '.b64'  : 'application/mime',
        '.bh'   : ('application/x-blakhole',
                   'application/mac-binhex40'),
        '.bhx'  : 'application/mac-binhex40',
        '.bin'  : 'application/macbinary',
        '.bz2'  : 'application/bzip2',
        '.cab'  : 'application/cab',
        '.cbr'  : 'application/x-rar',
        '.cbt'  : 'application/x-tar',
        '.cbz'  : 'application/zip',
        '.cp'   : 'application/x-cpio',
        '.cpio' : 'application/x-cpio',
        '.deb'  : 'application/x-deb',
        '.dgc'  : 'application/x-dgca-compressed',
        '.dms'  : 'application/x-dms',
        '.ear'  : 'application/java-archive',
        '.egg'  : 'application/zip',
        '.exe'  : 'application/x-dosexec',
        '.gca'  : 'application/x-gca-compressed',
        '.gz'   : 'application/x-gzip',
        '.hqx'  : 'application/mac-binhex40',
        '.ipk'  : 'application/x-tar',
        '.iso'  : 'application/x-iso9660-image',
        '.j'    : 'application/java-archive',
        '.jar'  : 'application/java-archive',
        '.lha'  : 'application/lzh',
        '.lzh'  : 'application/lzh',
        '.lzo'  : 'application/x-lzop',
        '.lzx'  : 'application/lzx',
        '.mim'  : 'application/mime',
        '.msi'  : 'application/msi',
        '.pak'  : 'application/zip',
        '.pk3'  : 'application/zip',
        '.rar'  : 'application/x-rar',
        '.rpm'  : 'application/x-rpm',
        '.rz'   : 'application/x-rzip',
        '.rsn'  : 'application/x-rar',
        '.sea'  : 'application/sea',
        '.sfark': 'application/x-extension-sfark',
        '.sh'   : 'application/x-sh',
        '.shar' : 'application/x-shar',
        '.sit'  : 'application/x-stuffit',
        '.sitx' : 'application/x-stuffitx',
        '.slp'  : 'application/x-slp',
        '.sqx'  : 'application/x-squeeze',
        '.tar'  : 'application/x-tar',
        '.taz'  : 'application/x-compress',
        '.tbz2' : 'application/bzip2',
        '.tgz'  :  'application/x-gzip',
        '.tz'   : 'application/x-compress',
        '.uu'   : 'application/x-uuencode',
        '.uue'  : 'application/x-uuencode',
        '.war'  : ('application/x-webarchive', 'application/java-archive'),
        '.xar'  : 'application/x-xar',
        '.xpi'  : 'application/x-xpinstall',
        '.xx'   : 'application/x-xx-encoded',
        '.xxe'  : 'application/x-xx-encoded',
        '.ync'  : 'application/x-yenc-encoded',
        '.yenc' : 'application/x-yenc-encoded',
        '.z'    : 'application/x-compress',
        '.zip'  : 'application/zip',
        '.zoo'  : 'application/x-zoo',
}
"""Fallback extension-to-mimetype mappings for when header detection fails or
is unavailable.

@note: I didn't use the C{mimetypes} module because its purpose is apparently
to quickly guess mimetypes in an application which uses them for something
with a reasonably large margin for error and a bias towards common filetypes.
(eg. icon-selection, HTTP headers)

Having unball would gain no benefit from adding local mime<->ext mappings and
would suffer if it relied on them completely. The C{mimetypes} lookup semantics
also differ from unball's desired behaviour in certain subtle ways.
"""

FALLBACK_DESCRIPTIONS = {
        'application/x-blakhole'        : "BlakHole archive. The only extraction tools for this seem to be Windows-only.",
        'application/x-dgca-compressed' : "DGCA archive. The only known site for these is in Japanese and the only extraction tool seems to be Windows-only.",
        'application/x-dosexec'         : "DOS/Windows Executable. It may be a self-extracting archive, but all attempts to extract it failed.",
        'application/x-gca-compressed'  : "GCA archive. The only known site for these is in Japanese and the only extraction tool seems to be Windows-only.",
        'application/x-iso9660-image'   : "ISO9660 CD/DVD image. To extract files from this, use a virtual disc drive like CDEmu (Linux) or DaemonTools (Windows)",
        'application/msi'               : "Microsoft Installer package. If you trust it, you can use Wine's msiexec tool to install it.",
        'application/x-shar'            : "self-extracting shell archive. For security reasons, it has not been executed automatically.",
        'application/x-sh'              : "shell script. If the file is more than a few hundred kilobytes in size, it's almost definitely a 'shar' or or 'makeself' archive. "
                                          "At present, unball lacks a method to extract such archives without executing untrusted code.",
        'application/x-stuffitx'        : "StuffIt X archive. As of this writing, extractors for this format exist only for Windows and MacOS X.",
        'application/zip'               : "Zip archive. However, extraction failed. If the cause was an unsupported compression method, try installing p7zip.",
}
"""A list of explanations for formats unball cannot currently extract on its
own.

@todo: Rework this so it'll be called as a final 'fallback' should no existing
command work.
@todo: Also rework it so it's used to describe nested unpacks.
(The [archive %s contained a single file which|file %s] may be a...)
"""

def which(execName, execpath=None):
    """Like the UNIX which command, this function attempts to find the given
    executable in the system's search path. Returns C{None} if it cannot find
    anything.

    @todo: Find the copy I extended with win32all and use it here."""
    if 'nt' in os.name:
        suffixes = ['.exe', '.com', '.bat', '.cmd']
    else:
        suffixes = []

    if isinstance(execpath, basestring):
        execpath = execpath.split(os.pathsep)
    elif not execpath:
        execpath = os.environ.get('PATH', os.defpath).split(os.pathsep)

    for path in execpath:
        fullPath = os.path.join(os.path.expanduser(path), execName)
        if os.path.exists(fullPath):
            return fullPath
        for suffix in suffixes:
            if os.path.exists(fullPath + suffix):
                return fullPath + suffix
    return None  # Couldn't find anything.

def mimeToExtractor(mime):
    """Given a mimetype, return a list of possible extraction tools.
    Uses L{Extractor.isViable} to check whether potentials are present.

    @param mime: The mimetype of the file to be extracted.
    @type mime: C{str}|C{tuple}|C{list}

    @returns: List of possible extraction tools.
    @rtype C{list}
    """

    if isinstance(mime, basestring):
        mime = (mime, )

    possibilities = []
    for mimetype in mime:
        if mimetype in EXTRACTORS:
            extractors = EXTRACTORS[mimetype]
            if isinstance(extractors, Extractor):
                possibilities.append(extractors)
            else:
                possibilities.extend(extractors)

    return [x for x in possibilities if x.isViable()]

def pathToMimetype(path):
    """Given a path, identify the mimetype (tries L{headerToMimetype}, falls
    back to extension mapping if the result isn't in EXTRACTORS)

    @note: Resolves symlinks to avoid application/x-not-regular-file
    """
    path = os.path.realpath(path)
    mime = headerToMimetype(path).lower()

    # Extension fallback for if the mimetype checker doesn't identify it.
    if not mime in EXTRACTORS:
        ext = os.path.splitext(path)[1].lower()
        if ext in EXTENSIONS:
            mime = EXTENSIONS[ext]

    return mime

class NamedTemporaryFolder(object):
    """Context manager wrapping C{tempfile.mkdtemp} with automatic cleanup.

    @todo: Look into using the version from http://bugs.python.org/issue5178
    """

    tmp = None  # Path to created folder. Filled in __enter__

    def __init__(self, suffix='', prefix=tempfile.template, dir=None):
        """
        @param suffix: See C{tempfile.mkstemp}
        @param prefix: See C{tempfile.mkstemp}
        @param dir: See C{tempfile.mkstemp}
        """
        self.suffix = suffix
        self.prefix = prefix
        self.parent = dir or tempfile.gettempdir()

    def __enter__(self):
        """
        @returns: The path to the temporary directory.
        @rtype: C{str}
        @raises OSError: Errors returned by C{mkdtemp} on failure.
        """
        self.tmp = tempfile.mkdtemp(suffix=self.suffix,
                                    prefix=self.prefix,
                                    dir=self.parent)
        return self.tmp

    def __exit__(self, exc_type, exc_value, traceback):
        """
        @raises OSError: Failed to delete temporary directory.
        @note: This will not follow the directory across renames.
        """
        if os.path.exists(self.tmp):
            shutil.rmtree(self.tmp)

class TempTarget(NamedTemporaryFolder):
    """
    Context manager for atomic archive extraction.

    Extends L{NamedTemporaryFolder} to rename and preserve the folder on a
    clean exit.

    @note: Because of the fixed C{target} value, the recommended use of this
      context manager is to instantiate it within the C{with} statement.

    """
    def __init__(self, target, suffix="", prefix=tempfile.template,
                 parent=None, collapse=False):
        """
        @param suffix: See C{tempfile.mkstemp(suffix)}
        @param prefix: See C{tempfile.mkstemp(prefix)}
        @param parent: See C{tempfile.mkstemp(dir)}

        @param target: Target directory to move to on successful completion.
        @param collapse: If C{True} and the temporary directory contains only
            one entry when the context manager exits, rename that file or
            folder to the target path rather than the temporary directory.

        @type target: C{basestring}
        @type collapse: C{bool}

        @todo: Figure out how to get rid of the "src" parameter.
        """
        super(TempTarget, self).__init__(suffix, prefix, parent)

        self.target = target
        self.collapse = collapse

    def __exit__(self, exc_type, exc_value, traceback):
        """
        @raises OSError: Target path exists.
        @raises OSError: Failed to delete temporary directory
        @raises NothingProducedError: The context exited cleanly but the temp
          directory contained no files.
        """
        try:
            #TODO: Unit test to ensure exception are always passed through.
            if exc_type:
                return  # Just let the "finally" clause fire on errors

            move_from = self.tmp
            if self.collapse:
                contents = os.listdir(self.tmp)
                if len(contents) == 1:
                    move_from = os.path.join(self.tmp, contents[0])

            #TODO: --overwrite handling should probably go here?
            if os.path.exists(self.target):
                raise OSError(errno.EEXIST, os.strerror(errno.EEXIST),
                              self.target)
            else:
                shutil.move(move_from, self.target)

            # You have to set the umask to retrieve it. :(
            umask = os.umask(022)
            os.umask(umask)

            # The target directory was created by mkdtemp, so loosen the
            # permissions according to the umask.
            perms = os.path.isdir(self.target) and 0777 or 0666
            os.chmod(self.target, perms & (~umask))
        finally:
            super(TempTarget, self).__exit__(exc_type, exc_value, traceback)

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
    mime = pathToMimetype(srcFile)
    extractors = mimeToExtractor(mime)
    if not extractors:
        if mime in FALLBACK_DESCRIPTIONS:
            #TODO: Replace this with a logging call for easy disabling
            print("%s seems to be a(n) %s" % (
                    srcFile, FALLBACK_DESCRIPTIONS[mime]))
            raise UnsupportedFiletypeError("Filetype recognized but "
                                           "unsupported: %s" % srcFile)
        elif mime in EXTRACTORS:
            raise NoExtractorError("Filetype supported but no viable "
                                   "extractors found: %s" % srcFile)
        else:
            raise UnsupportedFiletypeError(
                    "Not a known archive type: %s" % srcFile)

    #TODO: Rewrite all this temp directory handling as a context manager.

    prefer_contained_name = True  # TODO: Make this configurable
    context = TempTarget(os.path.join(targetDir, os.path.basename(srcFile)),
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
        if len(contents) == 0:
            raise NothingProducedError("Operation completed but temp "
                "folder is empty for %s" % context.target)
        elif (len(contents) == 1 and level < RECURSION_LIMIT and
                os.path.isfile(os.path.join(tempTarget, contents[0]))):
                # Handle nesting like .tar.7z
            #TODO: Should I go as far as explicitly collapsing nested
            #      containing folders?
            try:
                tryExtract(os.path.join(tempTarget, contents[0]), None,
                           level + 1)
            except UnsupportedFiletypeError:
                pass
            else:
                os.remove(os.path.join(tempTarget, contents[0]))

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
        except UnsupportedFiletypeError, err:
            cautions.append(archive)
        except NothingProducedError, err:  # Bug trap triggered
            failures.append(str(err))
            last_errcode = 1
        except IOError, err:  # Permissions error
            failures.append(str(err))
            last_errcode = 2
        except OSError, err:  # Path error (eg. target exists or not a dir)
            failures.append(str(err))
            last_errcode = 3
        except NoExtractorError, err:  # Could not find suitable extractor
            failures.append(str(err))
            last_errcode = 4
        except subprocess.CalledProcessError, err:  # Extractor failed
            if err.returncode >= 0:
                failures.append(str(err))
                last_errcode = 5
            else:
                last_errcode = 6
                break
        except Exception, err:   # Unknown error
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
