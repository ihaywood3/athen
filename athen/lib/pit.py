#!/usr/bin/python

import logging, re, time, email.utils, datetime
from dateutil.relativedelta import relativedelta as rd
from email.mime.application import MIMEApplication

try:
    import pudb
except: pass
import myldap, config, rtf, hl7.emit
from registry import *

"""A simple PIT generator
Example grabbed from http://www.healthintersections.com.au/example.pit
"""

template = """001 ATHEN                                          07 01/07/2006
002 
003 Report Run Number: {run:4} Created:   {date:10 }     at    {time:5}:00
004 Surgery: {id:5} Reports: {date:10 } {time:5}:00  to  {date:10 } {time:5}:00    
009 ---------------------------------------------------------------------------
010 {recipient:32                   }            {provider_number:8}
019 ---------------------------------------------------------------------------
020 Your Ref.   Patient Name                   Lab Ref.        Test
021             {patient_name:31              }LABREFERENCE    LETTER
029 ---------------------------------------------------------------------------
100 Start Patient  :      {patient_name:0}
101                       {address:0}
104                       Birthdate: {dob:10  }    Age: {age_unit:1}{age:3}   Sex: {sex:1}
105                       Telephone: {telephone:10}
109 
110 Your Reference :      
111 Lab Reference  :      LABREFERENCE
112 Medicare Number:      {medicare:12}
115 Phone Enquiries:      ATHEN enquiries                  0359867709
119 
121 Referred by....:      {recipient:0}
123 Addressee      :      {recipient:32                  }  {provider_number:8}
129 
200 Start of Result:
201 Specimen       :
203 Requested      :      {date:10 }
204 Collected      :      {date:10 }  {time:5}
205 Name of Test   :      LETTER
206 Reported       :      {date:10 }  {time:5}
207 Confidential   :      Y
208 Test Category  :      R
211 Requested Tests:      LETTER
212 RequestComplete:      Y
299 
{content:0}
309 
319 
390 End of Report  :
399 ---------------------------------------------------------------------------
999 END OF LISTING - Run Number:{run:4}  {date:10 }  {time:5}:00"""


def subst(enput,txt):
    orig_length = len(txt)+2
    field, sz = txt.strip().split(':')
    sz = int(sz)
    if sz > 5 and sz != orig_length:
        logging.warn("for field {} nominated length {} real length {}".format(field,sz,orig_length))
    txt = enput.get(field,"")
    if sz == 0: return txt # zero size means just return, don't try any clever padding
    if len(txt) > sz:
        logging.warn("reducing field {} to size {}".format(field,sz))
        return txt[:sz]
    while len(txt) < sz:
        if field == 'age':
            txt = " "+txt # age gets right-padded
        else:
            txt = txt+" " # the rest get left-padded
    return txt
    

def replace_header1(m):
    title = m.group(1)
    title = upper(title)
    return "\n\n~SBLDSUND~"+title+"~EBLDEUND~\n\n"

def replace_header2(m):
    title = m.group(1)
    return "\n\n~SBLDSUND~"+title+"~EBLDEUND~\n\n"

def replace_header3(m):
    title = m.group(1)
    return "\n\n~SBLD~"+title+"~EBLD~\n\n"


def fix_lines2(doc):
    """a generator to sort out lines in a free text document"""

    doc = re.sub("[\u2028\u2029]*\uEF05([^\uEF06]+)\uEF06[\u2028\u2029]*",replace_header1,doc)
    doc = re.sub("[\u2028\u2029]*\uEF07([^\uEF08]+)\uEF08[\u2028\u2029]*",replace_header2,doc)
    doc = re.sub("[\u2028\u2029]*\uEF09([^\uEF0A]+)\uEF0A[\u2028\u2029]*",replace_header3,doc)

    doc = re.sub("\uEF02([^\uEF03]+)\uEF03([^\uEF04]+)\uEF04",r"\2 (see \1)",doc)

    doc = doc.replace(BOLD, "~SBLD~")
    doc = doc.replace(EBOLD, "~EBLD~")
    doc = doc.replace(UND, "~SUND~")
    doc = doc.replace(EUND, "~EUND~")

    doc = doc.replace(PARA,"\n\n")
    doc = doc.replace(LINE,"\n")
    doc = doc.strip()
    lines = doc.split("\n")
    for l in lines:
        if len(l) <= 76:
            yield l.strip()
        else:
            words = l.split()
            out = ""
            while len(words) > 0:
                if len(out)+1+len(words[0]) <= 76:
                    out = out+" "+words[0]
                    del words[0]
                elif len(out) == 0:
                    # its a big word
                    yield words[0][:75]+"-"
                    words[0] = words[0][75:]
                else:
                    yield out.strip()
                    out = ""
            if out: yield out.strip()


def fix_lines(doc):
    return "\n".join("301 "+i for i in fix_lines2(doc))

def make_pit_common(ld):
    enput = {}
    t = ld.get_document_time()
    enput['time'] = t.strftime("%H:%M")
    enput['date'] = t.strftime("%d/%m/%Y")
    if not ld.has('birthdate'):
        raise NotPossible()
    age = rd(datetime.datetime.now(),ld.birthdate)
    if age.months == 0 and age.years == 0:
        enput['age_unit'] = 'D'
        enput['age'] = "{: >3}".format(age.days)
    elif age.years < 2:
        enput['age_unit'] = "M"
        enput['age'] = "{: >3}".format(age.months+(age.years*12))
    else:
        enput['age_unit'] = "Y"
        enput['age'] = "{: >3}".format(age.years)
    enput['dob'] = ld.birthdate.strftime("%d/%m/%Y")
    if not ld.has('sex'):
        raise NotPossible()
    enput['sex'] = ld.sex
    if not ld.has('patient_name'):
        raise NotPossible()
    enput['patient_name'] = ld.patient_name
    if ld.has('patient_address'):
        enput['address'] = ld.patient_address
    else:
        enput['address'] = ""
    enput['recipient'] = util.fullname(ld.recipient)
    pn = ld.recipient.get("provider_number",None)
    if not pn:  # its unlikely the target EMR can dp much useful without a PN
        raise NotPossible()
    enput['provider_number'] = pn
    # in the current implementation, we never know these
    enput['medicare'] = ""
    enput['telephone'] = ""
    run_no,initials = ld.get_run_data() 
    enput['filename'] = ld.get_filestub()+'.PIT'
    enput['run'] = "{:0>4}".format(run_no % 10000) # to fit into 4 digits we incur repetition every 10,000 messages from this sender.
    # use first five letters of username for the PIT "surgery ID"
    enput['id'] = "{: <5}".format(ld.recipient['email'].upper()[:5])
    return enput

def make_pit_text(ld):
    enput = make_pit_common(ld)
    enput['content'] = fix_lines(ld.getvalue())
    return pit_finish(enput)

def pit_finish(enput):
    s = re.sub(r"{(.+?)}", lambda m: subst(enput,m.group(1)), template)
    s = s.replace("\n","\r\n") # use old Internet/Windows-style newlines
    s = hl7.emit.hl7_escape_non_ascii(s) # translate some common non-ASCII characters
    # to make sure this works we encode and then decode here, anything > 127 that gets to here will get
    # mapped to "?"
    s = bytes(s,"us-ascii","replace")
    # there's no standard MIME type for PIT
    # in fact AFAICT this is the first time anyone has tried to
    # send PIT via SMTP e-mail. "application/x-pit" therefore is entirely my own invention
    mt = MIMEApplication('',_subtype="x-pit")
    mt['Content-Disposition'] = 'attachment; filename="{}"'.format(enput['filename'])
    mt.set_payload(hl7.emit.quopri_hl7(s))
    del mt['Content-Transfer-Encoding']
    mt['Content-Transfer-Encoding'] = 'quoted-printable' 
    mt.set_param('name',enput['filename'])
    return mt

def make_pit_rtf(ld):
    enput = make_pit_common(ld)
    if ld.has("original_rtf"):
        trtf = ld.original_rtf
    else:
        trtf = rtf.convert_rtf_from_ld(ld.getvalue())
    trtf = trtf.replace("\n","")
    trtf = trtf.replace("\r","")
    # rtf as a single line: not documented anywhere but rumoured to work
    enput['content'] = "301 "+trtf
    return pit_finish(enput)

register_outputter("pit-ft",make_pit_text,'PIT - plain text') # PIT/formatted text (for consistency with hl7-**-ft, even though PIT and HL7 "formatted text" are not equivalent
register_outputter("pit-rtf",make_pit_rtf,'PIT - RTF embedded') # PIT/Rich Text Format


def extract_addressee(pit):
    m  = re.search(r"123.*: *([^ ]+)", pit)
    if m:
        return m.group(1).strip()
    else:
        return None
