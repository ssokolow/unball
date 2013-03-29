"""Wrappers and from-mimetype lookup code for archive extractors

@todo: Will unstuff and cabextract handle self-extracting cabs?
       (If so, add application/cab to the .exe list)
@todo: Figure out a better syntax for specifying extractor arguments.
       (especially destination directories)
"""

__author__  = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2.0 or later"

import os, subprocess

from .util import BinYes, UnballError, which

#{ Exceptions

class UnsupportedFiletypeError(UnballError):
    """Raised when the given mimetype is completely unsupported regardless of
    conditions."""
class NoExtractorError(UnsupportedFiletypeError):
    """Raised when a mimetype is supported but no viable extractor was found"""

#}
#{ Generic Classes

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

    def _make_target_filename(self, srcPath, destDir,
                              srcExt=None, destExt=None):
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

#}
#{ Specific Extractor Classes (Python stdlib)

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

#}
#{ Specific Extractor Classes (subprocesses)

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

#}
#{ Pseudo-Extractor Classes

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
#}


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

    extractors = [x for x in possibilities if x.isViable()]
    if extractors:
        return extractors
    else:
        if mime in FALLBACK_DESCRIPTIONS:
            raise UnsupportedFiletypeError(FALLBACK_DESCRIPTIONS[mime])
        elif mime in EXTRACTORS:
            raise NoExtractorError(mime)
        else:
            raise UnsupportedFiletypeError(mime)

EXTRACTORS = {
        'application/x-7z-compressed':
            (Extractor('7z', 'x'),
             Extractor('7za', 'x'),
             Extractor('7zr', 'x'),
             Extractor('sqc', 'x')),
        'application/x-ace-compressed':
            (Extractor('unace-bin', 'x', '-y'),
             Extractor('unace', 'x', '-y'),
             Extractor('sqc', 'x')),
        'application/x-adf':
            (Extractor('unadf'),
             Extractor('readdisk'),
             Extractor('e-readdisk')),
        'application/x-adz':
            PipeExtractor('gunzip', '.adz', '.adf'),
        'application/x-alz':
            Extractor('unalz'),
        'application/x-ar':
            Extractor('ar', 'x'),
        'application/x-arc':
            Extractor('arc', 'x'),
        'application/arj':
            (Extractor('arj', 'x', '-y'),
             Extractor('unarj', 'x'),
             Extractor('sqc', 'x')),
        'application/bzip2':
            (PipeExtractor('bunzip2', '.bz2'),
             BZip2Extractor()),
        'application/cab':
            TryAll(
                Extractor('cabextract'),
                Extractor('unshield'),
                Extractor('sqc', 'x')),
        'application/x-compress':
            (PipeExtractor('uncompress.real', '.z'),
             PipeExtractor('uncompress', '.z')),
        'application/x-cpio':
            Extractor('cpio', '--force-local', '--quiet', '-idI'),
        'application/x-deb':
            Extractor('ar', 'x'),
        'application/x-dosexec':
            [],  # See below for how this works
        'application/x-diskmasher':
            (Extractor('xdms', 'u'),
             NamedOutputExtractor('undms', '.dms', '.adf')),
        'application/x-gzip':
            (PipeExtractor('gunzip', '.gz'),
             GZipExtractor()),
        'application/lzh':
            (Extractor('lha', 'x'),
             Extractor('sqc', 'x')),
        'application/lzx':
            Extractor('unlzx', '-x'),
        'application/x-lzop':
            Extractor('lzop', '-x',),
        'application/macbinary':
            (SitExtractor(),
             Extractor('macunpack', '-f')),
        'application/mac-binhex40':
            (SitExtractor(),
             Extractor('uudeview', '-i')),
        'application/mime':
            Extractor('uudeview', '-ib'),
        'application/msi':
            Extractor('7z', 'x'),
        'application/x-rar':
            (Extractor('unrar', 'x', '-y', '-p-'),
             Extractor('rar', 'x', '-y', '-p-'),
             Extractor('sqc', 'x')),
        'application/x-rpm':
            (Extractor('rpm2cpio'),
             Extractor('rpm2targz')),
        'application/x-rzip':
            NamedOutputExtractor(['runzip', '-k'], '.rz',
                                 outfile_option='-o '),
        'application/x-extension-sfark':
            Extractor('sfarkxtc'),
        'application/x-slp':
            Extractor('alien', '-g'),
            # FIXME: Untested for lack of a .slp file
        'application/x-squeeze':
            Extractor('sqc', 'x'),
        'application/x-stuffit':
            SitExtractor(),
        'application/x-tar':
            (Extractor('tar', 'xf'),
             TarExtractor()),
        'application/x-uuencode':
            (Extractor('uudeview', '-i'),
             Extractor('uudecode'),
             UUDecoder()),
        'application/x-xar':
            Extractor('xar', '-xf'),
        'application/x-xx-encoded':
            (Extractor('uudeview', '-i'),
             Extractor('xxdecode')),
        'application/x-yenc-encoded':
            (Extractor('uudeview', '-i'),
             Extractor('ydecode'),
             Extractor('yydecode')),
        'application/zip':
            (Extractor('7z', 'x'),
             Extractor('7za', 'x'),
             Extractor('unzip', '-q'),
             ZipExtractor(),
             Extractor('jar', 'xf'),
             Extractor('sqc', 'x')),
        'application/x-zoo':
            (Extractor('unzoo', '-x'),
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
        'application/x-archive': 'application/x-ar',
        'application/x-ace': 'application/x-ace-compressed',
        'application/x-arj': 'application/arj',
        'application/x-bcpio': 'application/x-cpio',
        'application/x-bz2': 'application/bzip2',
        'application/x-bzip': 'application/bzip2',
        'application/x-bzip2': 'application/bzip2',
        'application/x-compressed': 'application/x-gzip',
        'application/x-dms': 'application/x-diskmasher',
        'application/x-gtar': 'application/x-tar',
        'application/java-archive': 'application/zip',
        'application/x-lha': 'application/lzh',
        'application/x-lharc': 'application/lzh',
        'application/x-lzh': 'application/lzh',
        'application/x-lzh-archive': 'application/lzh',
        'application/x-lzx': 'application/lzx',
        'application/x-macbinary': 'application/macbinary',
        'application/x-mime-encoded': 'application/mime',
        'application/x-msi': 'application/msi',
        'application/x-msiexec': 'application/msi',
        'application/x-ole-storage': 'application/msi',
        'application/sea': 'application/x-stuffit',
        'application/x-sea': 'application/x-stuffit',
        'application/x-sh': 'application/x-shar',
        'application/stuffit-lite': 'application/x-stuffit',
        'application/x-sv4cpio': 'application/x-cpio',
        'application/vnd.ms-cab-compressed': 'application/cab',
        'application/x-webarchive': 'application/x-tar',
        'application/x-xpinstall': 'application/zip',
        'application/x-zip': 'application/zip',
        'x-compress': 'application/x-compress',
        'x-gzip': 'application/x-gzip',
        'x-uuencode': 'application/x-uuencode',
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
        'application/x-blakhole': "BlakHole archive. The only extraction "
            "tools for this seem to be Windows-only.",
        'application/x-dgca-compressed': "DGCA archive. The only known site "
            "for these is in Japanese and the only extraction tool seems to "
            "be Windows-only.",
        'application/x-dosexec': "DOS/Windows Executable. It may be a self-"
            "extracting archive, but all attempts to extract it failed.",
        'application/x-gca-compressed': "GCA archive. The only known site "
            "for these is in Japanese and the only extraction tool seems to "
            "be Windows-only.",
        'application/x-iso9660-image': "ISO9660 CD/DVD image. To extract "
            "files from this, use a virtual disc drive like CDEmu (Linux) or"
            " DaemonTools (Windows)",
        'application/msi': "Microsoft Installer package. If you trust it, "
            "you can use Wine's msiexec tool to install it.",
            #TODO: I believe 7zip can now unpack MSIs.
        #'application/x-shar': "self-extracting shell archive. For security "
        #    "reasons, it has not been executed automatically.",
        'application/x-sh': "shell script. If the file is more than a few "
            "hundred kilobytes in size, it's almost definitely a 'shar' or "
            "'makeself' archive. At present, unball lacks a method to "
            "extract such archives without executing untrusted code.",
        'application/x-stuffitx': "StuffIt X archive. As of this writing, "
            "extractors for this format exist only for Windows and MacOS X.",
        'application/zip': "Zip archive. However, extraction failed. If the "
            "cause was an unsupported compression method, try installing "
            "p7zip.",
}
"""A list of explanations for formats unball cannot currently extract on its
own.

@todo: Rework this so it'll be called as a final 'fallback' should no existing
command work.
@todo: Also rework it so it's used to describe nested unpacks.
(The [archive %s contained a single file which|file %s] may be a...)
"""

for key, target_key in aliases.items():
    for target in (EXTRACTORS, FALLBACK_DESCRIPTIONS):
        if target_key in target:
            if key in target:
                raise Exception("OVERWRITE: %s -> %s" % (target_key, key))
            target[key] = target[target_key]
del aliases, key
