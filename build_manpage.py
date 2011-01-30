# -*- coding: utf-8 -*-
"""
This file is originally from http://andialbrecht.wordpress.com/2009/03/17/creating-a-man-page-with-distutils-and-optparse/
Modified by René Neumann to support for a "See Also" section.

Retrieved from at 2009-08-27 16:21 EST from
http://bazaar.launchpad.net/~necoro/portato/trunk/annotate/454/build_manpage.py

Modified by Stephan Sokolow:
 - Docstring cleanup
 - Capitalize the command name in the header to match other manpages
 - Fix compatibility with %prog in usage lines when run from setup.py or paver.
"""

import datetime
from distutils.command.build import build
from distutils.core import Command
from distutils.errors import DistutilsOptionError
import optparse, os

class build_manpage(Command):
    """build_manpage command -- Generate man page from OptionParser --help"""
    description = 'Generate manpage from --help'

    user_options = [
        ('output=', 'O', 'output file'),
        ('parser=', None, 'module path to optparser (e.g. mymod:func)'),
        ('seealso=', None, 'list of manpages to put into the SEE ALSO section (e.g. bash:1)')
        ]

    def initialize_options(self):
        self.output = None
        self.parser = None
        self.seealso = None

    def finalize_options(self):
        if self.output is None:
            raise DistutilsOptionError('\'output\' option is required')
        if self.parser is None:
            raise DistutilsOptionError('\'parser\' option is required')

        self.ensure_string_list('seealso')

        mod_name, func_name = self.parser.split(':')
        fromlist = mod_name.split('.')
        try:
            mod = __import__(mod_name, fromlist=fromlist)
            self._parser = getattr(mod, func_name)()
        except ImportError, err:
            raise
        self._parser.formatter = ManPageFormatter()
        self._parser.formatter.set_parser(self._parser)
        self._today = datetime.date.today()

    def _markup(self, txt):
        return txt.replace('-', '\\-')

    def _write_header(self):
        version = self.distribution.get_version()
        appname = self.distribution.get_name()
        ret = []
        ret.append('.TH %s 1 %s "%s v.%s"\n' % (self._markup(appname.upper()),
                                      self._today.strftime('%Y\\-%m\\-%d'), appname, version))
        description = self.distribution.get_description()
        if description:
            name = self._markup('%s - %s' % (self._markup(appname),
                                             description.splitlines()[0]))
        else:
            name = self._markup(appname)
        ret.append('.SH NAME\n%s\n' % name)
        synopsis = self._parser.get_usage()
        if synopsis:
            for name in (appname, 'setup.py', 'appname', 'paver'):
                if synopsis.startswith(name):
                    synopsis = synopsis.replace('%s ' % name, '')
                    break
            ret.append('.SH SYNOPSIS\n.B %s\n%s\n' % (self._markup(appname),
                                                      synopsis))
        long_desc = self.distribution.get_long_description()
        if long_desc:
            ret.append('.SH DESCRIPTION\n%s\n' % self._markup(long_desc))
        return ''.join(ret)

    def _write_options(self):
        ret = ['.SH OPTIONS\n']
        ret.append(self._parser.format_option_help())
        return ''.join(ret)

    def _write_seealso (self):
        ret = []
        if self.seealso is not None:
            ret.append('.SH "SEE ALSO"\n')

            for i in self.seealso:
                name, sect = i.split(":")

                if len(ret) > 1:
                    ret.append(',\n')

                ret.append('.BR %s (%s)' % (name, sect))

        return ''.join(ret)

    def _write_footer(self):
        ret = []
        appname = self.distribution.get_name()
        author = '%s <%s>' % (self.distribution.get_author(),
                              self.distribution.get_author_email())
        ret.append(('.SH AUTHORS\n.B %s\nwas written by %s.\n'
                    % (self._markup(appname), self._markup(author))))
       # homepage = self.distribution.get_url()
       # ret.append(('.SH DISTRIBUTION\nThe latest version of %s may '
       #             'be downloaded from\n'
       #             '.UR %s\n.UE .\n'
       #             % (self._markup(appname), self._markup(homepage),)))
        return ''.join(ret)

    def run(self):
        self.announce('Writing man page %s' % self.output)
        manpage = []
        manpage.append(self._write_header())
        manpage.append(self._write_options())
        manpage.append(self._write_footer())
        manpage.append(self._write_seealso())

        dirname = os.path.dirname(os.path.abspath(self.output))
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        stream = open(self.output, 'w')
        stream.write(''.join(manpage))
        stream.close()


class ManPageFormatter(optparse.HelpFormatter):

    def __init__(self,
                 indent_increment=2,
                 max_help_position=24,
                 width=None,
                 short_first=1):
        optparse.HelpFormatter.__init__(self, indent_increment,
                                        max_help_position, width, short_first)

    def _markup(self, txt):
        return txt.replace('-', '\\-')

    def format_usage(self, usage):
        return self._markup(usage)

    def format_heading(self, heading):
        if self.level == 0:
            return ''
        return '.TP\n%s\n' % self._markup(heading.upper())

    def format_option(self, option):
        result = []
        opts = self.option_strings[option]
        result.append('.TP\n.B %s\n' % self._markup(opts))
        if option.help:
            help_text = '%s\n' % self._markup(self.expand_default(option))
            result.append(help_text)
        return ''.join(result)


build.sub_commands.append(('build_manpage', None))
