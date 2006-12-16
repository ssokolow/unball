#!/usr/bin/env python
"""
Name: unball unit test script
Copyright 2006 Stephan Sokolow

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
"""

__author__ = "Stephan Sokolow (deitarion)"
__revision__ = "$Revision$"

import os, shutil, tempfile, unittest

# Files which may be added to the test sources dir without being test sources.
excluded = ['.DS_Store']

# Maps return codes to their meanings.
retcodes = {
            0: 'Extracted OK', 
            1: 'A bug trap was triggered',
            2: 'Could not make temp dir',
            3: 'Could not change directories', 
            4: 'Could not find requested unarchiving tool',
            5: 'Archive tool returned an error', 
            6: 'Could not move files to target dir',
            7: 'Could not delete temporary files/dirs',
            32512: 'Unknown. Could not find a required command in PATH?'
           }

count_omit = ['jartest.j', 'jartest.jar', 'eartest.ear', 'wartest.war', 'mscompress.tx_']

def makeTests(path):
    """
    Dynamically generate a set of unball unit tests for a given file.
    Used to allow per-format testing of unball in a simple manner.
    """
    filename = os.path.split(path)[1]
    class UnballTestSet(unittest.TestCase):
        """Test unball with a specific archive"""
        def setUp(self):
            """Prepare a temporary test tree in the filesystem."""
            self.workdir = tempfile.mkdtemp('-unballtest')
            # All dirs have spaces in them in order to ensure there are no
            #  space-related bugs remaining.
            self.pwd_dir = os.path.join(self.workdir, 'pwd dir')
            self.srcdir  = os.path.join(self.workdir, 'src dir')
            self.srcfile = os.path.join(self.srcdir , filename)
            self.destdir = os.path.join(self.workdir, 'dest dir')
            
            os.makedirs(self.srcdir)
            os.makedirs(self.destdir)
            os.makedirs(self.pwd_dir)
            shutil.copyfile(path, self.srcfile)
            
            self.oldcwd = os.getcwdu()
        def tearDown(self):
            """Make sure the test tree gets deleted."""
            os.chdir(self.oldcwd)
            shutil.rmtree(self.workdir)
        
        def testImplicitDestination(self):
            """Testing unball %s with implicit destination"""
            os.chdir(self.destdir)
            
            #callstring = 'unball "%s" &> /dev/null' % self.srcfile
            callstring = 'unball "%s" <&- >&- 2>&-' % self.srcfile
            retcode = os.system(callstring)
            if (len(retcodes) > retcode): 
                retstring = retcodes[retcode]
            else: 
                retstring = "Unknown code"

            self.failIf(retcode, "Unball returned error code %s (%s)" % (retcode, retstring))
            self.failUnless(len(os.listdir(self.srcdir)) == 1, 
                            "%s extracted to the source dir without being asked to." % callstring)
            self.failUnless(os.path.exists(self.srcfile), 
                            "%s didn't prevent the original archive from being destroyed." % callstring)
            self.failIf(len(os.listdir(self.destdir)) > 1, 
                            "%s didn't bundle a multi-file archive into one folder." % callstring)
            self.failIf(len(os.listdir(self.destdir)) < 1, 
                            "%s didn't extract anything to the target dir." % callstring)
            
            newdir = os.path.join(self.destdir, os.listdir(self.destdir)[0])
            if os.path.isdir(newdir):
                self.failIf(len(os.listdir(newdir)) <= 1, 
                            "%s created a wrapper dir without needing to" % callstring)
                self.failIf(newdir.endswith('.tar'), 
                            "%s didn't strip .tar from the name of the newly created dir." % callstring)
                if not filename in count_omit:
                    self.failIf(len(os.listdir(newdir)) != 9, 
                                "%s did not extract the correct number of files. Got %s but expected %s" % (callstring, len(os.listdir(newdir)), 9))
            
        def testExplicitDestination(self):
            """Testing unball %s with explicit destination"""
            
            os.chdir(self.pwd_dir)
            
            #callstring = 'unball -d "%s" "%s" &> /dev/null' % (self.destdir, self.srcfile)
            callstring = 'unball -d "%s" "%s" <&- >&- 2>&-' % (self.destdir, self.srcfile)
            retcode = os.system(callstring)
            if (len(retcodes) > retcode): 
                retstring = retcodes[retcode]
            else: 
                retstring = "Unknown code"
            
            self.failIf(retcode, "Unball returned error code %s (%s)" % (retcode, retstring))
            self.failIf(len(os.listdir(self.pwd_dir))  > 0, 
                        "%s extracted to $PWD dir when given an explicit destination." % callstring)
            self.failUnless(len(os.listdir(self.srcdir))  == 1, 
                            "%s extracted to the source dir without being asked to." % callstring)
            self.failUnless(os.path.exists(self.srcfile), 
                            "%s didn't prevent the original archive from being destroyed." % callstring)
            self.failIf(len(os.listdir(self.destdir))  > 1, 
                            "%s didn't bundle a multi-file archive into one folder." % callstring)
            self.failIf(len(os.listdir(self.destdir))  < 1, 
                            "%s didn't extract anything to the target dir." % callstring)
            
            newdir = os.path.join(self.destdir, os.listdir(self.destdir)[0])
            if os.path.isdir(newdir):
                self.failIf(len(os.listdir(newdir)) <= 1, 
                            "%s created a wrapper dir without needing to." % callstring)
                self.failIf(newdir.endswith('.tar'), 
                            "%s didn't strip .tar from the name of the newly created dir." % callstring)
                if not filename in count_omit:
                    self.failIf(len(os.listdir(newdir)) != 9, 
                                "%s did not extract the correct number of files. Got %s but expected %s" % (callstring, len(os.listdir(newdir)), 9))
        
        def testSameDestination(self):
            """Testing unball %s with samedir  destination"""
            os.chdir(self.pwd_dir)
            
            #callstring = 'unball -D "%s" &> /dev/null' % self.srcfile
            callstring = 'unball -D "%s" <&- >&- 2>&-' % self.srcfile
            retcode = os.system(callstring)
            if (len(retcodes) > retcode): 
                retstring = retcodes[retcode]
            else: 
                retstring = "Unknown code"
            
            self.failIf(retcode, "Unball returned error code %s (%s)" % (retcode, retstring))
            self.failUnless(os.path.exists(self.srcfile), 
                            "%s didn't prevent the original archive from being destroyed." % callstring)
            self.failIf(len(os.listdir(self.srcdir)) > 2, 
                            "%s didn't bundle a multi-file archive into one folder." % callstring)
            self.failIf(len(os.listdir(self.srcdir)) < 2, "%s didn't extract anything." % callstring)

            #TODO: Duplicate the newdir test here with the necessary extra complexity.        
                    
        testImplicitDestination.__doc__ = testImplicitDestination.__doc__ % filename
        testExplicitDestination.__doc__ = testExplicitDestination.__doc__ % filename
        testSameDestination.__doc__ = testSameDestination.__doc__ % filename
    
    return UnballTestSet

def testdir(path):
    """Generate and run a set of tests for the given directory full of archives."""
    path = os.path.abspath(path)
    print 'Testing directory "%s" ...' % os.path.split(path)[1]
    print "NOTE: stdin, stdout, and stderr are closed for these tests. If extraction of ACE files freezes, it's a regression."

    i, j, l = os.path.isdir, os.path.join, os.listdir
    f = [j(path, arch) for arch in l(path) if not (i(arch)) and not arch in excluded]
    f.sort()
    t = [unittest.makeSuite(makeTests(path)) for path in f]
    return unittest.TestSuite(t)
    
if __name__ == '__main__':
    if os.system('which unball'):
        print "ERROR: Cannot find unball in your PATH."
	print "Did you install to the default location and forget to add /usr/local/bin to the PATH?"
	#FIXME: There should be an option to use the un-installed unball for tests.
    else:
        try:
            import testoob
            testoob.main(testdir('test sources'), verbose=True)
        except ImportError:
            tester = unittest.TextTestRunner(verbosity=2)
            tester.run(testdir('test sources'))
