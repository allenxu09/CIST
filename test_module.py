import unittest
import json
from IdiomSearcher import IdiomSearcher

class TestMultipleSearches(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.searcher = IdiomSearcher('res/idioms_new.json')

    def test(self):
        with open('res/test_searches.json', 'r', encoding='utf-8') as f:
            file_test_cases = json.load(f)

        for i, test_case in enumerate(file_test_cases):
            expression = test_case["expression"]
            expected = test_case["expected"]
            result = self.searcher.search(expression)

            with self.subTest(f"测试用例 #{i + 1}: {expression}"):
                if expected == "not_empty":
                    self.assertNotEqual(result, [], f"Search #'{expression}' should not be null.")
                elif expected == "empty":
                    self.assertEqual(result, [], f"Search #'{expression}' should be null.")
                elif isinstance(expected, list):
                    self.assertEqual(list(result), list(expected), f"Search #'{expression}' doesn't output expectedly.")

if __name__ == '__main__':
    unittest.main()