"""
@todo: Use the following to set up an internal header matcher:
    - http://www.fileformat.info/format/arc/corion.htm
    - http://www.fileformat.info/format/zoo/corion.htm
@todo: Fix this so it handles "one ext to multiple mimetypes" mappings properly
@todo: The extension checker needs to be rewritten to support *.??_
(Oh, and what does compress.exe do with extensions longer than 3 characters?)

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

__author__  = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2.0 or later"

import errno, os

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
            mime = mime.rstrip(',; \t\n')
            return mime

    del mime_checker
except ImportError:  # TODO: Can magic.open or mime_checker.load() fail?
    import subprocess

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
        mime = mime.rstrip(',; \t\n')
        return mime

def pathToMimetype(path, desired_types=None):
    """Given a path, identify the mimetype (tries L{headerToMimetype}, falls
    back to extension mapping if the result isn't in EXTRACTORS)

    @param desired_types: If provided and the resolved mimetype is not in
        this list, attempt to look up an alternative based on the file's
        extension.
    @type desired_types: C{list(str)}

    @note: Resolves symlinks to avoid application/x-not-regular-file
    """
    path = os.path.realpath(path)
    mime = headerToMimetype(path).lower()

    # Extension fallback for if the mimetype checker doesn't identify it.
    if not mime in desired_types:
        ext = os.path.splitext(path)[1].lower()
        if ext in EXTENSIONS:
            mime = EXTENSIONS[ext]

    return mime

EXTENSIONS = {
        '.7z': 'application/x-7z-compressed',
        '.a': 'application/x-ar',
        '.ace': 'application/x-ace-compressed',
        '.adf': 'application/x-adf',
        '.adz': 'application/x-adz',
        '.alz': 'application/x-alz',
        '.ar': 'application/x-ar',
        '.arc': 'application/x-arc',
        '.arj': 'application/arj',
        '.b64': 'application/mime',
        '.bh': ('application/x-blakhole',
                'application/mac-binhex40'),
        '.bhx': 'application/mac-binhex40',
        '.bin': 'application/macbinary',
        '.bz2': 'application/bzip2',
        '.cab': 'application/cab',
        '.cbr': 'application/x-rar',
        '.cbt': 'application/x-tar',
        '.cbz': 'application/zip',
        '.cp': 'application/x-cpio',
        '.cpio': 'application/x-cpio',
        '.deb': 'application/x-deb',
        '.dgc': 'application/x-dgca-compressed',
        '.dms': 'application/x-dms',
        '.ear': 'application/java-archive',
        '.egg': 'application/zip',
        '.exe': 'application/x-dosexec',
        '.gca': 'application/x-gca-compressed',
        '.gz': 'application/x-gzip',
        '.hqx': 'application/mac-binhex40',
        '.ipk': 'application/x-tar',
        '.iso': 'application/x-iso9660-image',
        '.j': 'application/java-archive',
        '.jar': 'application/java-archive',
        '.lha': 'application/lzh',
        '.lzh': 'application/lzh',
        '.lzo': 'application/x-lzop',
        '.lzx': 'application/lzx',
        '.mim': 'application/mime',
        '.msi': 'application/msi',
        '.pak': 'application/zip',
        '.pk3': 'application/zip',
        '.rar': 'application/x-rar',
        '.rpm': 'application/x-rpm',
        '.rz': 'application/x-rzip',
        '.rsn': 'application/x-rar',
        '.sea': 'application/sea',
        '.sfark': 'application/x-extension-sfark',
        '.sh': 'application/x-sh',
        '.shar': 'application/x-sh',
        '.sit': 'application/x-stuffit',
        '.sitx': 'application/x-stuffitx',
        '.slp': 'application/x-slp',
        '.sqx': 'application/x-squeeze',
        '.tar': 'application/x-tar',
        '.taz': 'application/x-compress',
        '.tbz2': 'application/bzip2',
        '.tgz': 'application/x-gzip',
        '.tz': 'application/x-compress',
        '.uu': 'application/x-uuencode',
        '.uue': 'application/x-uuencode',
        '.war': ('application/x-webarchive', 'application/java-archive'),
        '.xar': 'application/x-xar',
        '.xpi': 'application/x-xpinstall',
        '.xx': 'application/x-xx-encoded',
        '.xxe': 'application/x-xx-encoded',
        '.ync': 'application/x-yenc-encoded',
        '.yenc': 'application/x-yenc-encoded',
        '.z': 'application/x-compress',
        '.zip': 'application/zip',
        '.zoo': 'application/x-zoo',
}
