from merge import Merger
import os

template= 'fixtures/simple-template.svg'
datafile= 'fixtures/testdata.csv'
output_pattern= '/tmp/$file$'
expected=  '/tmp/helloworld.svg'
if os.path.exists(expected):
    os.remove(expected)
Merger().invoke( template, datafile, output_file_pattern=output_pattern)
