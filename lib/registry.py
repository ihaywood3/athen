"""
a basic registry system and helper classes for mailfilter and its plugin modules
(otherwise the plugins would have circular dependency on mailfilter)
"""

from collections import OrderedDict
import io, os

import util

class NotPossible(Exception):
    """
    Conversion to a medical document is not possible
    (but e-mail should still be passed through, this is not a 
    fatal error in any way
    NOTE: can be raised at final rendering stage too.
    """
    pass


registry_mime = {}

def register_mime(mime,thing):
    """
    Register a handler for a particular MIME type
    thing is a callable, called thing(data,ld)
          data = the data content
          ld = a LogicalDocument
          Returns nothing
          Can raise NotPossible
    """
    registry_mime[mime] = thing

registry_filetypes = {}

def register_filetype(suffix,thing):
    """
    Register a handler for a particular filetype
    thing is a callable, called thing(data,ld)
          data= the data content
          ld = a LogicalDocument
          Returns nothing
          Can raise NotPossible
    """
    registry_filetypes[suffix] = thing

registry_outputs = OrderedDict({})

def register_outputter(typ,thing,doc=None):
    """
    Register an outputter for a particular 
    type
    thing is a callable: called thing(ld)
        ld = a LogicalDocument 
        returns a MIME Message (with its Content-Type,
        Content-Disposition,
         and filename all set appropriately.
        thing can raise NotPossible
    """
    registry_outputs[typ] = (thing, doc)


def null_handler(x):
    raise NotPossible

register_outputter("none",null_handler,"None")

def call_output(typ, ld):
    thing, doc = registry_outputs[typ]
    return thing (ld)
    
def get_all_outputs():
    """Return a list of all output names
    """
    return list(registry_outputs.keys())

def get_all_outputs_docs():
    return [(label, registry_outputs[label][1]) for label in registry_outputs]



# these are "official" Unicode markup codes

LINE="\u2028"
PARA="\u2029"

# now use some 'spare' Unicode points for our very basic markup;
# range EF00−EF7F is unassigned even according to the "unoffical" registry
# at http://www.kreativekorp.com/ucsur/

BOLD="\uEF00"
EBOLD="\uEF01"
HREF="\uEF02"
MHREF="\uEF03" # "middle" of the HREF: i.e end of the URL and beginning of link text
EHREF="\uEF04"
HDR1="\uEF05"
EHDR1="\uEF06"
HDR2="\uEF07"
EHDR2="\uEF08"
HDR3="\uEF09"
EHDR3="\uEF0A"
UND="\uEF0B"
EUND="\uEF0C"

class LogicalDocument:
    """
    Represents a logical medical document, maybe in potentia
    (i.e it may never acquire enough params to be renderable)
    """

    def __init__(self,userdb):
        self.data = {}
        self.userdb = userdb
        self.content = io.StringIO()

    def write(self,text):
        self.content.write(text)

    def __getattr__(self,i):
        return self.data[i.lower()]

    def __setattr__(self,i,j):
        if i in ['data','content','userdb']:
            super(LogicalDocument, self).__setattr__(i, j)
        else:
            self.data[i.lower()] = j

    def has(self, x):
        return x in self.data

    def getvalue(self):
        return self.content.getvalue()

    def get_run_data(self):
        """Returns (run_no, initals)
        Result is cached only one call to underlying DB per 
        LogicalDocument instance"""
        if not 'run_data' in self.data:
            self.data['run_data'] = self.userdb.get_run_from_sender(self.data['sender']['email'],(self.data['sender'].get('firstname',"")+" "+self.data['sender'].get('surname','')).strip())
        return self.data['run_data']

    def get_patient_id(self):
        """Return patient ID based on listed name and DOB
        Uses userdb"""
        if not 'patient_id' in self.data:
            _, firstname, surname = util.break_name(self.data['patient_name'])
            self.data['patient_id'] = self.userdb.get_patient_id(surname,firstname,self.data['birthdate'])
        return self.data['patient_id']

    def get_unique_id(self):
        """
        Generate a systemwide forever-unique ID for this document
        Basically it's just a concatenation of the username and
        the run_data
        The run data IS guaranteed unique for this user as it
        has a unique 3 letter code for sender and then a counter
        for each document from that sender  (held in the user DB, see userdb.py)
        """
        run_no, initial = self.get_run_data()
        return initial+'-'+str(run_no)+os.environ['USER']

    def get_filestub(self):
        """Conveinence method generates a 8-letter stub
        for 8.3 DOS style filenames
        uses initials and run_no
        -> run_no must be 5 digits so this will wrap every 100,000 files
        for a given sender, so unlikely get_unique_id is it is not guaranteed unique forever
        """
        run_no, initial = self.get_run_data()
        run_no = run_no % 100000
        return "{}{:0>5}".format(initial,run_no)

    def get_document_time(self):
        if 'document_time' in self.data:
            return self.data['document_time']
        else:
            return util.now_tz()

