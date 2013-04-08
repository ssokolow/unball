#!/usr/bin/env python
import os, sys

_a = lambda path: os.path.join(os.path.dirname(__file__), path)

if __name__ == '__main__' and not 'flake8' in sys.modules:
    #FIXME: Why does this segfault flake8 under PyPy?
    from setuptools import setup
    #from distutils.core import setup

    from build_manpage import build_manpage

    setup(
        name="Unball",
        version="0.2.99.0",  # TODO: Figure out how to DRY this.
        description="'Do what I mean' archive commands for your shell",
        long_description="""
            Simple console wrappers which handle decisions like
            "what format is it in?" and "Do I need to create a folder for it?"
            for you.
            """,  # TODO: Rewrite this when I finish making this an API with
                  # console reference implementations.
        author="Stephan Sokolow",
        author_email="http://www.ssokolow.com/ContactMe",  # No spam harvesting
        url='https://github.com/ssokolow/unball',
        #download_url="https://github.com/ssokolow/unball",
        license="License :: OSI Approved :: GNU General Public License (GPL)",
        classifiers=[
            "Environment :: Console",
            "Intended Audience :: End Users/Desktop",
            "Intended Audience :: System Administrators",
            # "Intended Audience :: Developers",
            # TODO: For when I finish the API rework.
            "License :: OSI Approved :: GNU General Public License (GPL)",
            "Operating System :: POSIX",
            #"Operating System :: OS Independent",
            # TODO: For when the stdlib-based zip/tar support is ready.
            "Programming Language :: Python",
            #TODO: Add support for Python 3 and an appropriate classifier
            "Topic :: System :: Archiving",
            "Topic :: Utilities",
        ],

        packages=['unball'],
        scripts=['src/moveToZip'],
        zip_safe=True,

        #TODO: Forget setuptools. Just replace this with a stub script.
        entry_points={
            'console_scripts': [
                'unball = unball.main:main',
            ],
        },
        data_files=[
            ('share/man/man1', ['build/man/unball.1']),
        #    ('share/apps/konqueror/servicemenus', [
        #        'src/servicemenus/unball.desktop',
        #        'src/servicemenus/moveToZip.desktop'
        #    ]),
            ('libexec/thunar-archive-plugin', ['src/unball.tap'])
        ],

        cmdclass={'build_manpage': build_manpage},
        test_suite='run_test.get_tests',

        #TODO: I need to rewrite build_manpage to build more than one
        options={
            'build_manpage': {
                'output': 'build/man/unball.1',
                'parser': 'unball.main:get_opt_parser',
            },
        },
    )
