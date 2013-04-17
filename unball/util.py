"""Utility classes and functions"""
__author__  = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 2.0 or later"

import errno, os, shutil, tempfile

#{ Exceptions

class UnballError(Exception):
    """Base class for all Unball-internal exceptions."""

#}
#{ Classes

class BinYes(object):
    """A file-like object mimicking /bin/yes to be passed to stdin so
    broken commands like unace don't hang."""
    @staticmethod
    def read(*args):
        return "y\n"

    @staticmethod
    def fileno():
        return None

class NamedTemporaryFolder(object):
    """Context manager wrapping C{tempfile.mkdtemp} with automatic cleanup.

    @todo: Look into using the version from http://bugs.python.org/issue5178
    @todo: Is it even possible to make a context manager reentrant within a
           single instance?
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
            umask = os.umask(0o022)
            os.umask(umask)

            # The target directory was created by mkdtemp, so loosen the
            # permissions according to the umask.
            perms = os.path.isdir(self.target) and 0o777 or 0o666
            os.chmod(self.target, perms & (~umask))
        finally:
            super(TempTarget, self).__exit__(exc_type, exc_value, traceback)

#}

def which(execName, execpath=None):
    """Like the UNIX which command, this function attempts to find the given
    executable in the system's search path. Returns C{None} if it cannot find
    anything.

    @todo: Find the copy I extended with win32all and use it here.
    """
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
