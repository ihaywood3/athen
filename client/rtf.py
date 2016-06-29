#!/usr/bin/python

"""
Module for habndling RTF and other files and 
extracting relevant data
relies on https://pypi.python.org/pypi/pyth/
"""


from pyth.plugins.rtf15.reader import Rtf15Reader
from pyth.plugins.plaintext.writer import PlaintextWriter

import re

class ParsingError(Exception):
    pass
    
def parse_rtf(fname):
    """
    Load an RTF file
    return dictionary with patient/sender/receipient data
    and 'content': the file content"""
    with open(fname,"rb") as f:
        doc = Rtf15Reader.read(f)
        f.seek(0)
        orig = f.read()
    txt = PlaintextWriter.write(doc).getvalue()
    return parse_txt(txt,orig)

def parse_txt(txt,orig):
    d = {}
    m = re.search(r"Re: (.*), (.*)",txt)
    if m is None:
        raise ParsingException("Can't find Re: line")
    d['surname'] = m.group(1)
    d['firstname'] = m.group(2)
    d['patient_name'] = "{},{}".format(d['surname'],d['firstname'])
    after_re = txt[m.start():]
    m = re.search(r"Address: (.* [0-9]{4})",after_re)
    if m is None:
        raise ParsingException("Can't find address")
    d['address'] = m.group(1).strip()
    m = re.search(r"DOB: ([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",after_re)
    if m is None:
        raise ParsingError("Can't find DOB")
    d['dob'] = m.group(1)
    m = re.search(r"Medicare: ([0-9 /-]+)",after_re)
    if m:
        s = m.group(1)
        s = s.replace("/","")
        s = s.replace(" ","")
        s = s.replace("-", "")
        d['medicare'] = s
    else:
        d['medicare'] = ""  # Medicare number is optional
    m = re.search(r"phone: ([0-9 -]+)",after_re)
    if m:
        s = m.group(1)
        s = s.replace(" ","")
        s = s.replace("-","")
        if len(s) > 10 or len(s) < 5:
            raise ParsingError("not a valid telephone number")
        d['telephone'] = s
    else:
        d['telephone'] = "" # telephone is optional
    m = re.search(r"Sex: ([MFUT])",after_re,re.IGNORECASE)
    if m is None:
        raise ParsingError("Sex not specified")
    d['sex'] = m.group(1).upper()
    m = re.search(r"Email: (.*)",txt)
    if m is None:
        raise ParsingError("Can't find recipient email")
    d['recipient_email'] = m.group(1)
    m = re.search("Receipient: (.*)",txt)
    if m is None:
        raise ParsingError("Can't find recip[ent name")
    d['receipient'] = m.group(1)
    m = re.search("Receipient Provider Number: ([0-9A-Z]+)",txt)
    if m is None:
        d['provider_number'] = "" # optional: we don't always send to doctors
    else:
        d['provider_number'] = m.group(1)
    d['content'] = orig
    return d
    
if __name__=='__main__':
    parse_rtf('/home/ian/test.rtf')