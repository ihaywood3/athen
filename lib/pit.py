#!/usr/bin/python

import logging, re, time, email.utils
try:
    import pudb
except: pass
import myldap

SUBJECT_RE=re.compile(r"\[([A-Za-z\-' ]+, [A-Za-z\-' ]+) \((M|F)\) DOB: ?([0-9\/]+) (.+, .+ [0-9]{4})\] (.*)$", re.IGNORECASE)

"""A simple PIT generator
Example grabbed from http://www.healthintersections.com.au/example.pit
"""

template = """001 ATHEN                                          07 01/07/2006
002 
003 Report Run Number : {run:3} Created:   {date:10 }     at    {time:5}:00
004 Surgery: {id:5} Reports: {date:10 } {time:5}:00  to  {date:10 } {time:5}:00    
009 ---------------------------------------------------------------------------
010 {recipient:32                   }                {provider_number:8}
019 ---------------------------------------------------------------------------
020 Your Ref.   Patient Name                   Lab Ref.        Test
021             {patient_name:32              }LABREFERENCE    LETTER
029 ---------------------------------------------------------------------------
100 Start Patient  :      {patient_name:0}
101                       {address:0}
104                       Birthdate: {dob:10  } Age: {age_unit:1}{age:3}   Sex: {sex:1}
105                       Telephone: {telephone:10}
109 
110 Your Reference :      
111 Lab Reference  :      LABREFERENCE
112 Medicare Number:      {medicare:12}
115 Phone Enquiries:      ATHEN enquiries                  0359867709
119 
121 Referred by....:      {recipient:0}
123 Addressee      :      {recipient:0}
129 
200 Start of Result:
201 Specimen       :
203 Requested      :      {date:10 }
204 Collected      :      {date:10 }  {time:5}
205 Name of Test   :      LETTER
206 Reported       :      {date:10 }  {time:5}
207 Confidential   :      N
208 Test Category  :      R
211 Requested Tests:      LETTER
299 
{content:0}
309 
319 
390 End of Report  :
399 ---------------------------------------------------------------------------
999 END OF LISTING - Run Number: {run:3}  {date:10 }  {time:5}:00"""


def subst(enput,txt):
    field, sz = txt.split(':')
    sz = int(sz)
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

def fix_lines(lines):
    """a generator to sort out lines in a free text document"""
    for l in lines:
        l = str(l)
        while len(l) > 80:
            yield "301"+l[:80]
            l = l[80:]
        yield "301 "+l

def make(enput):
    enput['time'] = time.strftime("%H:%M")
    enput['date'] = time.strftime("%d/%m/%Y")
    try:
        day, month, year = [int(x) for x in enput['dob'].split('/')]
        if year < 25:
            year = year+2000
        elif year < 100:
            year = year + 1900
        assert year > 1850 and year < 2100
        assert day > 0 and day < 32
        assert month > 0 and month < 13
        enput['dob'] = "{:0>2}/{:0>2}/{}".format(day,month,year)
    except:
        logging.exception("date conversion failed")
        enput['dob'] = '01/01/1990'
    # FIXME: Howto get sensible values for these
    enput['run'] = '001'
    enput['id'] = '0000'
    if 'content' in enput:
        # we have an RTF file to embed
        # remove newlines from content so its one big line
        # FIXME: will this actually work?!
        enput['content'] = "301 "+enput['content'].replace("\n","").replace("\r","")
    else:
        s = enput['text']
        s = s.replace("\r","")
        s = "\n".join(list(fix_lines(s.split("\n"))))
        enput['content'] = s
    s = re.sub(r"{(.+?)}", lambda m: subst(enput,m.group(1)), template)
    s = s.replace("\n","\r\n") # use Internet/Windows style newlines
    return s

def make_from_email(msg):
    """Returns PIT message if email meets criteria otherwise None
    TODO: be smarter with attachments other than plain text: how to/if convert to PIT?
    """
    recipient_name, recipient_email = email.utils.parseaddr(msg["To"])
    # this is the same regex as in athen/server/roundcube/athen.js
    m = SUBJECT_RE.match(msg['Subject'])
    if m:
        doc = {}
        doc['patient_name'] = m.group(1)
        doc['sex'] = m.group(2)
        doc['dob'] = m.group(3)
        doc['address'] = m.group(4)
        #subject = m.group(5)
        try:
            hub = myldap.LDAP()
            r = hub.query(myldap.PUBLIC_BASE_DN,"(mail=%s)",recipient_email,fields=['providerNumber','cn'])
            if r:
                doc['provider_number'] = r[0]['providerNumber']
                if recipient_name == "":
                    recipient_name = r[0]['cn']
        except:
            logging.exception("couldn't get provider number from LDAP server - left blank")
        if recipient_name == "": 
            recipient_name = recipient_email
        doc['recipient'] = recipient_name
        text = ""
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                text += part.get_payload()
        if text != "":
            doc['text'] = text
            return make(doc)
    return None

def extract_addressee(pit):
    m  = re.search(r"123.*: *([^ ]+)", pit)
    if m:
        return m.group(1).strip()
    else:
        return None
