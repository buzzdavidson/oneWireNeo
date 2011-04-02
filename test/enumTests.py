
__author__ = 'sdavidson'

import unittest
from enum import Enum

#TODO
class EnumTests(unittest.TestCase):
    def setUp(self):
        self.enum = Enum('Dog','Cat','Fish')


    def testEmptyNotAllowed(self):
        try:
            enum = Enum()
        except AssertionError:
            pass
        else:
            fail("Expected assertion - empty enums not allowed")

    def testInclusion(self):
        assert self.enum.Cat

    def testInclusion_case(self):
        try:
            items = self.enum.cat
        except:
            pass
        else:
            fail("Expected assertion - enums are case sensitive")

    def testExclusion(self):
        try:
            items = self.enum.Frog
        except:
            pass
        else:
            fail("Expected assertion - item not in set")

    def testEquals(self):
        cat = self.enum.Cat
        anotherCat = self.enum.Cat

        assert (cat == anotherCat)

    def testLength(self):
        assert(self.enum.__len__() == 3)
            
if __name__ == '__main__':
    unittest.main()
