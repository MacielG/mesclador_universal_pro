import unittest
import os
from mesclador_universal_pro import FileMergerApp

class TestFileMerger(unittest.TestCase):
    def setUp(self):
        self.app = FileMergerApp()
        self.test_files = ["test1.txt", "test2.txt"]
        self.output_file = "output.txt"
        for filename in self.test_files:
            with open(filename, "w", encoding="utf-8") as f:
                if filename == "test1.txt":
                    f.write("Hello\nWorld\n")
                else:
                    f.write("Foo\nBar\n")

    def tearDown(self):
        for filename in self.test_files + [self.output_file]:
            if os.path.exists(filename):
                os.remove(filename)

    def test_detect_encoding(self):
        encoding = self.app._detect_encoding(self.test_files[0])
        self.assertIn(encoding.lower(), ["utf-8", "ascii", "utf8"])

    def test_add_files(self):
        self.app._add_files(self.test_files)
        self.assertEqual(len(self.app.selected_files), len(self.test_files))

    def test_merge_files_txt(self):
        self.app._add_files(self.test_files)
        self.app.output_name.delete(0, 'end')
        self.app.output_name.insert(0, self.output_file)
        self.app.output_format.set("TXT")
        self.app._start_merge()
        # Wait for thread to finish
        self.app._merge_thread.join()
        self.assertTrue(os.path.exists(self.output_file))
        with open(self.output_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hello", content)
        self.assertIn("Foo", content)

if __name__ == "__main__":
    unittest.main()import unittest
import os
from mesclador_universal_pro import FileMergerApp

class TestFileMerger(unittest.TestCase):
    def setUp(self):
        self.app = FileMergerApp()
        # Create some test files
        with open("test1.txt", "w", encoding="utf-8") as f:
            f.write("Hello\nWorld\n")
        with open("test2.txt", "w", encoding="utf-8") as f:
            f.write("Foo\nBar\n")

    def tearDown(self):
        # Remove test files
        for filename in ["test1.txt", "test2.txt", "output.txt"]:
            if os.path.exists(filename):
                os.remove(filename)

    def test_detect_encoding(self):
        encoding = self.app._detect_encoding("test1.txt")
        self.assertIn(encoding.lower(), ["utf-8", "ascii", "utf8"])

    def test_add_files(self):
        self.app._add_files(["test1.txt", "test2.txt"])
        self.assertEqual(len(self.app.selected_files), 2)

    def test_merge_files_txt(self):
        self.app._add_files(["test1.txt", "test2.txt"])
        self.app.output_name.delete(0, 'end')
        self.app.output_name.insert(0, "output")
        self.app.output_format.set("TXT")
        self.app._start_merge()
        # Wait for thread to finish
        self.app._merge_thread.join()
        self.assertTrue(os.path.exists("output.txt"))
        with open("output.txt", "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hello", content)
        self.assertIn("Foo", content)

if __name__ == "__main__":
    unittest.main()
