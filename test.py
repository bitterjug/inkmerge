import unittest 
from merge import Merger
import os

class test_invoke_merge(unittest.TestCase):

    def test_fail(self):
        print "foo"
        self.assertTrue(False)
    
    def test_inkvok(self):
        """ invoking the plugin with a template a data file from the 
        fixtures shoudl produce an output file
        """
        template= 'fixtures/simple-template.svg'
        datafile= 'fixtures/testdata.csv'
        output_pattern= '/tmp/$file'
        expected=  '/tmp/helloworld.svg'
        if os.path.exists(expected):
            os.remove(expected)
        Merger().invoke( template, datafile, output_file_pattern=output_pattern)
        self.assertTrue(os.path.exists(expected))

if __name__ == '__main__':
    unittest.main()
