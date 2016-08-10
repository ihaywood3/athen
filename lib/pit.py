#!/usr/bin/python

import logging, re, time

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
104                       Birthdate: {dob:8 }   Age: {age_unit:1}{age:3}   Sex: {sex:1}
105                       Telephone: {telephone:10}
109 
110 Your Reference :      
111 Lab Reference  :      LABREFERENCE
112 Medicare Number:      {medicare:12}
115 Phone Enquiries:      ATHEN enquiries                  0359867709
119 
121 Referred by....:      {recipient:32}
123 Addressee      :      {recipient:32}
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
{content}
309 
319 
390 End of Report  :
399 ---------------------------------------------------------------------------
999 END OF LISTING - Run Number: {run:3}  {date:10 }  {time:5}:00"""


def subst(input,txt):
    field, sz = txt.split(':')
    txt = input.get(field,"")
    if sz == 0: return txt
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

def make(input):
    input['time'] = time.strftime("%H:%M")
    input['date'] = time.strftime("%d/%m/%Y")
    try:
        day, month, year = [int(x) for x in input['dob'].split('/')]
        if year < 25:
            year = year+2000
        elif year < 100:
            year = year + 1900
        assert year > 1850 and year < 2100
        assert day > 0 and day < 32
        assert month > 0 and month < 13
        input['dob'] = "{:0>2}/{:0>2}/{}".format(day,month,year)
    except:
        raise Exception("date of birth not valid")
    # FIXME: Howto get sensible values for these
    input['run'] = '001'
    input['id'] = '0000'
    if 'content' in input:
        # we have an RTF file to embed
        # remove newlines from content so its one big line
        # FIXME: will this actually work?!
        input['content'] = "301 "+input['content'].replace("\n","").replace("\r","")
    else:
        s = input['text']
        s = s.replace("\r","")
        s = list(fix_lines(s.split("\n"))).join("\n")
        inpuit['content'] = s
    s = re.sub(r"{(.{8})}", lambda m: subst(input,m.group(1)), template)
    s = s.replace("\n","\r\n") # use Internet/Windows style newlines
    return s

def extract_addressee(pit):
    m  = re.search(r"123.*: *([^ ]+)", pit)
    if m:
        return m.group(1).strip()
    else:
        return None