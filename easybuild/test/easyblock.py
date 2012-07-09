import os
import re

from unittest import TestCase
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.systemtools import get_shared_lib_ext

class EasyBlockTest(TestCase):

    def setUp(self):
        self.eb_file = "tmp-test-file"
        f = open(self.eb_file, "w")
        f.write(self.contents)
        f.close()

    def tearDown(self):
        os.remove(self.eb_file)

    def assertErrorRegex(self, error, regex, call, *args):
        try:
            call(*args)
        except error, err:
            self.assertTrue(re.search(regex, err.msg))

class TestEmpty(EasyBlockTest):

    contents = "# empty string"

    def runTest(self):
        self.assertRaises(EasyBuildError, EasyBlock, self.eb_file)
        self.assertErrorRegex(EasyBuildError, "expected a valid path", EasyBlock, "")


class TestMandatory(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
"""

    def runTest(self):
        self.assertErrorRegex(EasyBuildError, "mandatory variable \w* not provided", EasyBlock, self.eb_file)

        self.contents += "\n".join(['homepage = "http://google.com"', 'description = "test easyblock"',
                                    'toolkit = {"name": "dummy", "version": "dummy"}'])
        self.setUp()

        eb = EasyBlock(self.eb_file)

        self.assertEqual(eb['name'], "pi")
        self.assertEqual(eb['version'], "3.14")
        self.assertEqual(eb['homepage'], "http://google.com")
        self.assertEqual(eb['toolkit'], {"name":"dummy", "version": "dummy"})
        self.assertEqual(eb['description'], "test easyblock")

class TestValidation(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"dummy", "version": "dummy"}
stop = 'notvalid'
"""

    def runTest(self):
        eb = EasyBlock(self.eb_file, validate=False)
        self.assertErrorRegex(EasyBuildError, "\w* provided \w* is not valid", eb.validate)

        eb['stop'] = 'patch'
        # this should now not crash
        eb.validate()

        # dummy toolkit, installversion == version
        self.assertEqual(eb.installversion(), "3.14")
        eb['toolkit'] = {"name": "GCC", "version": "4.6.3"}
        self.assertEqual(eb.installversion(), "3.14-GCC-4.6.3")

        os.chmod(self.eb_file, 0000)
        self.assertErrorRegex(EasyBuildError, "Unexpected IOError", EasyBlock, self.eb_file)
        os.chmod(self.eb_file, 0755)

        self.contents += "\nsyntax_error'"
        self.setUp()
        self.assertErrorRegex(EasyBuildError, "SyntaxError", EasyBlock, self.eb_file)

class TestSharedLibExt(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"dummy", "version": "dummy"}
sanityCheckPaths = { 'files': ["lib/lib.%s" % shared_lib_ext] }
"""

    def runTest(self):
        eb = EasyBlock(self.eb_file)
        self.assertEqual(eb['sanityCheckPaths']['files'][0], "lib/lib.%s" % get_shared_lib_ext())

class TestDependency(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"GCC", "version": "4.6.3"}
dependencies = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
builddependencies = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
"""

    def runTest(self):
        eb = EasyBlock(self.eb_file)
        # should include builddependencies
        self.assertEqual(len(eb.dependencies()), 4)
        self.assertEqual(len(eb.builddependencies()), 2)

        first = eb.dependencies()[0]
        second = eb.dependencies()[1]

        self.assertEqual(first['name'], "first")
        self.assertEqual(second['name'], "second")

        self.assertEqual(first['version'], "1.1")
        self.assertEqual(second['version'], "2.2")

        self.assertEqual(first['tk'], '1.1-GCC-4.6.3')
        self.assertEqual(second['tk'], '2.2-GCC-4.6.3')

        # same tests for builddependencies
        first = eb.builddependencies()[0]
        second = eb.builddependencies()[1]

        self.assertEqual(first['name'], "first")
        self.assertEqual(second['name'], "second")

        self.assertEqual(first['version'], "1.1")
        self.assertEqual(second['version'], "2.2")

        self.assertEqual(first['tk'], '1.1-GCC-4.6.3')
        self.assertEqual(second['tk'], '2.2-GCC-4.6.3')

        eb['dependencies'] = ["wrong type"]
        self.assertErrorRegex(EasyBuildError, "wrong type from unsupported type", eb.dependencies)

        eb['dependencies'] = [()]
        self.assertErrorRegex(EasyBuildError, "without name", eb.dependencies)
        eb['dependencies'] = [{'name': "test"}]
        self.assertErrorRegex(EasyBuildError, "without version", eb.dependencies)

class TestExtraOptions(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"GCC", "version": "4.6.3"}
toolkitopts = { "static": True}
dependencies = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
"""

    def runTest(self):
        eb = EasyBlock(self.eb_file)
        self.assertRaises(KeyError, lambda: eb['custom_key'])

        extra_vars = { 'custom_key': ['default', "This is a default key"]}

        eb = EasyBlock(self.eb_file, extra_vars)
        self.assertEqual(eb['custom_key'], 'default')

        eb['custom_key'] = "not so default"
        self.assertEqual(eb['custom_key'], 'not so default')

        self.contents += "\ncustom_key = 'test'"

        self.setUp()

        eb = EasyBlock(self.eb_file, extra_vars)
        self.assertEqual(eb['custom_key'], 'test')

        eb['custom_key'] = "not so default"
        self.assertEqual(eb['custom_key'], 'not so default')

        # test if extra toolkit options are being passed
        self.assertEqual(eb.toolkit().opts['static'], True)

class TestSuggestions(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"GCC", "version": "4.6.3"}
dependencis = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
"""

    def runTest(self):
        self.assertErrorRegex(EasyBuildError, "invalid variable dependencis", EasyBlock, self.eb_file)
        self.assertErrorRegex(EasyBuildError, "suggestions: dependencies", EasyBlock, self.eb_file)


