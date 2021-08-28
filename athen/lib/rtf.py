#!/usr/bin/python

"""
Module for habndling RTF and other files and 
extracting relevant data
FUTURE: relies on https://pypi.python.org/pypi/pyth/
"""


#from pyth.plugins.rtf15.reader import Rtf15Reader
#from pyth.plugins.plaintext.writer import PlaintextWriter

import re, io

from registry import *

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
    d['recipient_email'] = m.group(1).strip()
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

def convert_rtf_from_ld(text):
    """
    Take text from registry.LogicalDocument, using our funky markup, and convert to RTF
    """
    # first, all non-ASCII codes must be escaped
    # our target charset is "ANSI" aka "Windows-1259"
    # for this range the Unicode code points are the same as ISO-8859-1 and in turn the same same as the "ANSI" 
    for i in range(0xa0,0x100):
        text = text.replace(chr(i),"\\'{:x}".format(i))
    # and these are the Microsoft extensions which don't map cleanly from Unicode
    # based on table grabbed from http://ascii-table.com/ansi-codes.php
    text = text.replace("\u20AC","\\'80") # € 	Euro Sign
    # 81 Undefined
    text = text.replace("\u201A","\\'82") # ‚  Single Low-9 Quotation Mark
    text = text.replace("\u0192","\\'83") # ƒ  Latin Small Letter F With Hook
    text = text.replace("\u201E","\\'84") # „  Double Low-9 Quotation Mark
    text = text.replace("\u2026","\\'85") # …  Horizontal Ellipsis
    text = text.replace("\u2020","\\'86") # †  Dagger
    text = text.replace("\u2021","\\'87") # ‡  Double Dagger
    text = text.replace("\u02C6","\\'88") # ˆ  Modifier Letter Circumflex Accent
    text = text.replace("\u2030","\\'89") # ‰  Per Mille Sign
    text = text.replace("\u0160","\\'8a") # Š  Latin Capital Letter S With Caron
    text = text.replace("\u2039","\\'8b") # ‹  Single Left-pointing Angle Quotation Mark
    text = text.replace("\u0152","\\'8c") # Œ  Latin Capital Ligature Oe
    # 8D   Undefined
    text = text.replace("\u017D","\\'8e") # Ž  Latin Capital Letter Z With Caron
    # 8F Undefined
    # 90 Undefined
    text = text.replace("\u2018","\\'91") # ‘  Left Single Quotation Mark
    text = text.replace("\u2019","\\'92") # ’  Right Single Quotation Mark
    text = text.replace("\u201C","\\'93") # “  Left Double Quotation Mark
    text = text.replace("\u201D","\\'94") # ”  Right Double Quotation Mark
    text = text.replace("\u2022","\\'95") # •  Bullet
    text = text.replace("\u2013","\\'96") # –  En Dash
    text = text.replace("\u2014","\\'97") # —  Em Dash
    text = text.replace("\u02DC","\\'98") # ˜  Small Tilde
    text = text.replace("\u2122","\\'99") # ™  Trade Mark Sign
    text = text.replace("\u0161","\\'9a") # š  Latin Small Letter S With Caron
    text = text.replace("\u203A","\\'9b") # ›  Single Right-pointing Angle Quotation Mark
    text = text.replace("\u0153","\\'9c") # œ  Latin Small Ligature Oe
    # 9D  Undefined
    text = text.replace("\u017E","\\'9e") # ž  Latin Small Letter Z With Caron
    text = text.replace("\u0178","\\'9f") # Ÿ  Latin Capital Letter Y With Diaeresis
    # FIXME: some other way to map Unicode to RTF
    # now translate our markup
    text = text.replace(BOLD,"\\b ")
    text = text.replace(EBOLD,"\\b0 ")
    text = text.replace(UND,"\\ul ")
    text = text.replace(EUND,"\\ul0 ")
    # can't find spec for RTF URLs, but cribbing from how LibreOffice does it
    text = re.sub("\uEF02([^\uEF03]+)\uEF03([^\uEF04]+)\uEF04",r'{{\\field{\\*\\fldinst HYPERLINK "\1" }{\\fldrslt {\2}}}}',text)
    text = text.replace(LINE,r"\line ")
    text = text.replace(PARA,r"\par ")
    text = re.sub("[\u2028\u2029]*\uEF05([^\uEF06]+)\uEF06[\u2028\u2029]*",lambda x: r'{\par }{\b\ul\fs28 %s \par}<\par }' % x.group(1).upper(),text) # header 1 : old, underline, 14 point, upcase
    text = re.sub("[\u2028\u2029]*\uEF07([^\uEF08]+)\uEF08[\u2028\u2029]*",r"{\\par }{\\b\\fs28 \1 \\par}{\\par }",text) # header 2 bold 
    text = re.sub("[\u2028\u2029]*\uEF09([^\uEF0A]+)\uEF0A[\u2028\u2029]*",r"{\\par }{\\b \1 \\par}{\\par }",text) # header 3 bold
    return r'{\rtf1\ansi %s}' % text
