#!/usr/bin/env python
# Once we  enter affect, the document is available as document: elementTree
#TODO put all dependencies, including imported modules,into the .inx file.
# These two lines are needed if you don't put the script directly into
# the installation directory
from __future__ import with_statement
import  csv, os, tempfile, subprocess
from contextlib import closing
from copy import deepcopy
from collections import defaultdict
from subprocess import Popen, PIPE, STDOUT

#FIXME: looks like the string substitution on images is happening even to the  data body of embedded images. 
#TODO mac only?
#sys.path.append('/Applications/Inkscape.app/Contents/Resources/extensions')
import inkex

# suggest leave other formats to use of a tool like imagemagick rather than  
# make this plugin depend on that.

absref = u'{%s}absref'  % inkex.NSS['sodipodi']
absrefpath='//@sodipodi:absref'
href = u'{%s}href'  % inkex.NSS['xlink']
hrefpath='//@xlink:href'
DEFAULT_TEMPLATE='$%s$'
DEFAULT_FORMAT='svg'
DEFAULT_DPI='96'
UTF8='utf-8'
class Merger(inkex.Effect):
    """ Mail-merge effect class"""
    
    def __init__(self):
        """ Set up input parameters """
        # Call the base class constructor.kkkk
        # TODO shoudl use super(Merger, self).__init__() ?????
        inkex.Effect.__init__(self)
        # Define  options
        self.OptionParser.add_option('--extra-vars', action = 'store', type = 'string', dest = 'extraVars', default = '')
        self.OptionParser.add_option('--data-file', action = 'store', type = 'string', dest = 'dataFile' )
        self.OptionParser.add_option('--format', action = 'store', type = 'string', dest = 'outputFormat', default = DEFAULT_FORMAT ) 
        self.OptionParser.add_option('--output', action = 'store', type = 'string', dest = 'outputPattern', default = None )
        self.OptionParser.add_option('--tab', action="store", type="string", dest="tab", help="The selected UI-tab when OK was pressed") 
        self.OptionParser.add_option('--var-template', action="store", type="string", dest="varTemplate", default = DEFAULT_TEMPLATE)
        self.OptionParser.add_option('--pair-separator', action="store", type="string", dest="pairSep", default = "=>")
        self.OptionParser.add_option('--var-separator', action="store", type="string", dest="varSep", default = "|")
        self.OptionParser.add_option('--dpi', action="store", type="int", dest="dpi", default = DEFAULT_DPI)
        self.texts = None
        self.messages = []

    def replaceText(self, document, old, new):
        """ Traverse the whole tree and replace all occurrences of old with new"""
        textElements = document.xpath("//text()")
        for e in textElements:
            parent = e.getparent()
            t = parent.text
            if t != None:
                t2 = t.replace(old, new)
                parent.text = t2

    def replaceInAtt(self, node, fr, to, key):
        """ helper for replacing in attributes: """
        node.set(key, node.get(key).replace(fr, to))

    def replaceInImage(self, node, fr, to, key):
        """ helper for replacing in images """
        oldpath = node.get(key)
        newpath = oldpath.replace(fr, to)
        # message = "old [%s] new [%s]" % (oldpath, newpath)
        # inkex.debug(message)
        node.set(key, newpath)


    def replaceImages(self, document, old, new):
        """ Replace in sodipodi:absref and xlink:href image names"""
        for attribute in document.xpath(absrefpath, namespaces=inkex.NSS):
            self.replaceInImage(attribute.getparent(), old, new, absref)
        for attribute in document.xpath(hrefpath, namespaces=inkex.NSS):
            self.replaceInImage(attribute.getparent(), old, new, href)

    def replaceStyles(self, document, old, new):
        """ Replace in any style tag"""
        for a in document.xpath('//@style'):
            self.replaceInAtt(a.getparent(), old, new, 'style')

    def fixExtension(self, fileName, extension):
        """ add the extension to the file name if not already there """
        (base, ext) = os.path.splitext(fileName)
        if ext.lower() != extension.lower():
            fileName = fileName + extension
        return fileName

    def save(self,document):
        """ Save the given document to a temporary svg file"""
        currentFileName = None
        if self.options.outputFormat == 'svg':
            currentFileName = self.fixExtension(self.outputFileName, ".svg")
            outFile = open(currentFileName,'w')
            document.write(outFile)
            outFile.close()
        else:
            tmpFD, tempFileName = tempfile.mkstemp(suffix='.svg')
            try:
                with closing(os.fdopen(tmpFD, "w+b")) as tmpFile:
                    document.write(tmpFile)
                currentFileName = self.formatOutput(tempFileName)
            finally:
                os.unlink(tempFileName)
        self.messages.append("Generated " + currentFileName.rpartition('/')[2])

    def formatOutput(self, inputFile):
        """ convert temporary output file to the correct format"""
        format = self.options.outputFormat
        currentFileName = self.fixExtension(self.outputFileName,
            "." + self.options.outputFormat)
        exportOption = '--export-%s=%s'  % (format, currentFileName)
        dpiOption = '--export-dpi=%s' % self.options.dpi
        command = ['inkscape', '--without-gui', exportOption, dpiOption, inputFile]
        inkscape_output = Popen(command, shell=False, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT).communicate()[0]
        if (inkscape_output != ""):
            self.messages.append("Inkscape output: " + inkscape_output)
        #TODO use check_call to check for errors ?? inkscape doesn't seem to return != 0 even when,e.g. the input file is not there
        return currentFileName

    def replaceInOutputPattern(self, field, val):
        """ do the field substitution in the output file name pattern """
        self.outputFileName = self.outputFileName.replace(field,val)


    def resetOutputFileName(self):
        """ Reset the output field name pattern before each processing each row"""
        #TODO check if output file name pattern ends with appropriate extension and add if necessary
        if self.options.outputPattern:
            self.outputFileName=self.options.outputPattern
        else:
            raise Exception("No output file pattern found. ")


    def getTexts(self):
        if not self.texts:
            #TODO make this work with numeric fields rather than named ones
            varTemplate =  self.options.varTemplate
            pairSep = self.options.pairSep
            varSep = self.options.varSep
            self.texts = defaultdict(list)
            for (text, field) in [i.split(pairSep) for i in self.options.extraVars.split(varSep) if len(i)]:
                self.texts[field].append(text)
            for field in self.fieldNames:
                self.texts[field].append(varTemplate % field)
        return self.texts

    def fields(self, col):
        """ return list of texts to replace with the current col value including field name and extra text """
        fieldName = self.fieldNames[col]
        return self.getTexts()[fieldName]

    def process(self, row):
        """  Generate an output file for this data row"""
        self.resetOutputFileName()
        newDoc = deepcopy(self.document)
        col = 0 #FIXME consider the error case where the field names row has fewer columns than the data rows
        for datum in row:
            # remove control characters
            # datum = "".join([c for c in datum if ord(c) >= 32 ])
            datum = unicode(datum, UTF8)
            for field in self.fields(col):
                self.replaceText(newDoc, field, datum)
                self.replaceImages(newDoc, field, datum)
                self.replaceStyles(newDoc, field, datum)
                self.replaceInOutputPattern(field, datum)
            col = col + 1
        self.save(newDoc)

    def getData(self):
        """ Get the csv file, extract field names and process remaiing lines. """
        fileName = self.options.dataFile
        if fileName and os.path.isfile(fileName):
            dataReader = csv.reader(open(fileName, "U"))
        else:
            raise  Exception("Data file not found: [%s]" % fileName)
        self.fieldNames = dataReader.next()
        return dataReader

    def effect(self):
        """process data in data file and data in extraVars"""
        for row in self.getData():
            self.process(row)

    def invoke(self, 
            template, 
            data_file, 
            output_file_pattern='$file', 
            var_template=DEFAULT_TEMPLATE,
            output_format=DEFAULT_FORMAT,
            dpi=DEFAULT_DPI,
            ):
        """ Invoke the merge process from python passing arguments directly

        :param template Path to template svg file
        :param data_file Path to the data file 
        :param output_file_pattern with %s standing for column header value
        :param output_format output format 'svg' or 'pdf', default=svg
        :param dpi dpi for embedded images, 

        """
        args=['--data-file=%s' % data_file, 
              '--output=%s' % output_file_pattern, 
              '--var-template=%s' % var_template,
              '--format=%s' % output_format,
              '--dpi=%s'% dpi,
              template
              ]
        self.affect(args=args,output=False)

if __name__ == "__main__":
    # Create effect instance and apply it.
    Merger().affect()
