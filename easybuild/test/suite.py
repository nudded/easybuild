# toolkit should be first to allow hacks to work
import easybuild.test.toolkit as t
import easybuild.test.asyncprocess as a
import easybuild.test.easyblock as e
import easybuild.test.modulegenerator as mg
import easybuild.test.modules as m
import easybuild.test.filetools as f
import easybuild.test.repository as r
import easybuild.test.robot as robot

import unittest

suite = unittest.TestSuite(map(lambda x: x.suite(), [t, r, e, mg, m, f, a, robot]))
unittest.TextTestRunner().run(suite)