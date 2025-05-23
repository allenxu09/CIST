import unittest
from IdiomSearcher import IdiomSearcher

class TestCase(unittest.TestCase):

    def test(self):
        self.searcher = IdiomSearcher('res/idioms_new.json')
        self.assertIsNot(self.searcher.search('(#1 l%2 #2 #4) AND INCLUDE(un) AND EXCLUDE(sh,uo,d,ui,iang,x,j,q) AND NOT (?un # # #)'), [])
        self.assertIsNot(self.searcher.search('(#)'), [])

if __name__ == '__main__':
    unittest.main()
