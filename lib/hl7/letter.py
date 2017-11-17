"""
An emitter for HL7 letters (the REF message type)
"""

from . import emit

import config, util, rtf, registry
import datetime, base64, re
from email.mime.application import MIMEApplication
from registry import *
import email

# lifted from https://en.wikipedia.org/wiki/Postcodes_in_Australia#Australian_states_and_territories

POSTCODE_EXCEPTIONS=[
    ("4825","ALPURRURULAM","NT"),
    ("0872","ERNABELLA","SA"),
    ("0872","FREGON","SA"),
    ("0872","INDULKANA","SA"),
    ("0872","MIMILI","SA"),
    ("0872","NGAANYATJARRA-GILES","WA"),
    ("0872","GIBSON DESERT NORTH","WA"),
    ("0872","GIBSON DESERT SOUTH","WA"),
    #("2406","MUNGINDI","QLD"), there is also a Mungindi in NSW
    ("2540","HMAS CRESWELL","ACT"), # cue long and pointless discussion of whether the Jervis Bay base is technically part of the ACT 
    ("2540","JERVIS BAY","ACT"),
    ("2611","COOLEMAN","NSW"),
    ("2611","BIMBERI","NSW"),
    ("2611","BRINDABELLA","NSW"),
    ("2611","URIARRA","NSW"),
    ("2620","HUME","ACT"),
    ("2620","KOWEN FOREST","ACT"),
    ("2620","OAKS ESTATE","ACT"),
    ("2620","THARWA","ACT"),
    ("2620","TOP NAAS","ACT"),
    ("3500","PARINGI","NSW"),
    ("3585","MURRAY DOWNS","NSW"),
    ("3586","MALLAN","NSW"),
    ("3644","BAROOGA","NSW"),
    ("3644","LALALTY","NSW"),
    ("3691","LAKE HUME VILLAGE","NSW"),
    ("3707","BRINGENBRONG","NSW"),
    #("4380","MINGOOLA","NSW"), # there's a Queensland Mingoola but unclear how many live there...
    ("4377","MARYLAND","NSW")]



def _postcode_to_state(postcode,town):
    p0 = postcode[0]
    if p0 == "3" or p0 == "8":
        state = "VIC"
    elif p0 == "4" or p0 == "9":
        state = "QLD"
    elif p0 == "5":
        state = "SA"
    elif p0 == "6":
        state = "WA"
    elif p0 == "7":
        state = "TAS"
    elif p0 == "1":
        state = "NSW"
    else:
        # now it gets hard
        ip = int(postcode)
        if ip >= 800 and ip <= 999:
            state = "NT"
        elif (ip >= 200 and ip <= 299) or (ip >= 2600 and ip <= 2619) or (ip >= 2900 and ip <= 2920):
            state = "ACT"
        else:
            state = "NSW"
    for p2, t2, s2 in POSTCODE_EXCEPTIONS:
        if postcode == p2 and town == t2:
            state = s2
    return state

def get_xcn(person,cn_only=False):
    """Convert the title/firstname/surname dict to an XCN field dict"""
    # if no surname, we actually want to bug out
    if not 'surname' in person: raise registry.NotPossible
    xcn = {1:person['surname'], 
           2:person.get("firstname",""),
           5:person.get("title",""),
           9:"L"} # Legal name
    if 'provider_number' in person:
        xcn[0] = person['provider_number']
        xcn[8] = "AUSHICPR"
        if not cn_only:
            xcn[12] = "UPIN" # means Yank "Universal Physician provider Number", doesn't seem right to me to use in AU content, the offical examples (via MO) do this.
    return xcn

def make_prd(person):
    """"Comnvert the title/firstname/surname dict to a PRD segment dict"""
    if not 'surname' in person: raise registry.NotPossible
    # FIXME: support telephone nos and addresses too
    prd = {0:"PRD"}
    prd[2] = {0:person['surname'],1:person.get('firstname',''),4:person.get('title',''),6:'L'} # L = Legal name
    if 'provider_number' in person:
        prd[7] = (person['provider_number'],'AUSHICPR','UPIN')
    return prd

def doc_as_hl7_ft(ld):
    '''Turn our markuo into the HL7 Formatted Text type'''
    doc = ld.getvalue()
    doc = emit.hl7_escape(doc) # the stamdard HL7 escapes. do these first as we will insert \ of our own below
    doc = re.sub("[\u2028\u2029]*\uEF05([^\uEF06]+)\uEF06[\u2028\u2029]*",lambda m: "\\.br\\\\.br\\\\H\\"+m.group(1).upper()+"\\.br\\\\.br\\\\N\\",doc)
    doc = re.sub("[\u2028\u2029]*\uEF07([^\uEF08]+)\uEF08[\u2028\u2029]*",r"\\.br\\\\.br\\\\H\\\1\\N\\\\.br\\\\br.\\",doc)
    doc = re.sub("[\u2028\u2029]*\uEF09([^\uEF0A]+)\uEF0A[\u2028\u2029]*",r"\\.br\\\\.br\\\1\\.br\\\\.br\\",doc)

    doc = re.sub("\uEF02([^\uEF03]+)\uEF03([^\uEF04]+)\uEF04",r"\2 (see \1)",doc)

    doc = doc.replace(BOLD, "\\H\\")
    doc = doc.replace(EBOLD, "\\N\\")
    doc = doc.replace(UND, "\\H\\")
    doc = doc.replace(EUND, "\\N\\")
    # remove pointless terminal newlines
    doc = re.sub('['+PARA+LINE+']+\\Z','',doc)
    doc = doc.replace(PARA,"\\.br\\\\.br\\")
    doc = doc.replace(LINE,"\\.br\\")
    doc = emit.hl7_escape_non_ascii(doc)
    doc = bytes(doc,'us-ascii','replace')
    return doc

def make_hl7(style,embed,ld):
    """
    accept a LogicalDocument and produce an HL7 strucutre (a list of dicts representing segments)
    Two structures: ORU (i.e. like a path report), and REF (i.e  a "proper" referral)
    Two ways to embed the document: RTF blob (RTF), and HL7 Formatted Text (FT)
    """
    assert ld
    assert style in ['ORU','REF']
    assert embed in ['FT','RTF']
    for i in ['sender','recipient','patient_name','birthdate','sex']:
        if not ld.has(i):
            raise registry.NotPossible()
    semail = ld.sender['email']
    temail = ld.recipient['email']
    n = temail.split("@")
    tdomain = n[1]
    run_no,initials = ld.get_run_data()
    patient_name = ld.patient_name
    if "," in patient_name:
        n = patient_name.split(",")
        patient_firstname = n[1].strip()
        patient_surname = n[0].strip()
    else:
        patient_firstname, patient_surname = util.break_name(name)
    if " " in patient_firstname:
        n = patient_firstname.split(" ")
        patient_firstname = n[0]
        patient_auxnames = " ".join(n[1:])
        patient_auxnames = patient_auxnames.replace(".","")
        patient_auxnames = patient_auxnames.strip()
    else:
        patient_auxnames = ""
    if (not patient_firstname) or (not patient_surname):
        raise registry.NotPossible()
    msh = {0:"MSH",
           1:b'^~\\&',
           2:('ATHEN','ATHEN '+config.version,'L'),
           3:(semail,config.domain,"DNS"),
           5:(temail,tdomain,"DNS"),
           6:util.now_tz(), 
           9:ld.get_unique_id(),
           10:"P",
           15:"AL",
           16:"AUS",
           17:"ASCII",
           20:""  # force correct number of empty fields
           }
    pid = {0:"PID",
           1:"1",
           # standards say PID-3 is required. Have in-the-wild samples with it blank .We can only really generate fake IDs anyway. AHML complains about no PID-3
           3:(ld.get_patient_id(),"","",(semail,config.domain,"DNS")),
           5:(patient_surname,patient_firstname,patient_auxnames,"","","","L"),
           7:ld.birthdate,
           8:ld.sex,
           30:""}
    if ld.has('patient_address'):
        m = re.match(r"(.+), ?(.+) ?([0-9]{4})",ld.patient_address)
        if m:
            street = m.group(1)
            town = m.group(2)
            postcode = m.group(3)
            state = _postcode_to_state(postcode,town)
            pid[11] = (street,"",town,state,postcode,"AUS","C")
        else:
            pid[11] = (ld.patient_address,"",'','','','AUS','C')
    pv1 = {0:"PV1",
           1:"1",
           2:"O", # Outpatient. table 0004 pg 220
           8:get_xcn(ld.recipient),
           9:get_xcn(ld.recipient),
           52:""} # yes 52 frigging fields, even in 2.3.1
    obr = {0:'OBR',
           1:"1",
           3:(ld.get_unique_id(),config.domain,config.domain,'DNS'),
           4:("11488-4","Consultation Note","LN"),
           7:ld.get_document_time(),
           16:get_xcn(ld.recipient), # the "requesting doctor" doesn't make much sense for letters but EMRs may use it for the receiving doctor
           20:"LN="+ld.get_unique_id(), # black box field in HL7 official, AU standard has its own mini-language, page 21 of 2.3.1 4007.2 standards
           22:ld.get_document_time(),
           24:"PHY", # "physician note": used for all letters
           25:"F", # result status "F" = final result table 0123 page 325 2.3.1 Standards
           32:(get_xcn(ld.sender,True),ld.get_document_time(),ld.get_document_time()), # the "pathologist" and times are beginning and end of the "observation"
           45:""}
    obx = {0:"OBX",
           1:"1", # set number - increment for each OBX
           11:"F", # result status  F=final table 85 on page 527
           17:""}
    if embed == "FT":
        obx[3] =("11488-4","Consultation Note","LN")
        obx[2] = "FT"
        obx[5] = doc_as_hl7_ft(ld)
    elif embed == "RTF":
        obx[2] = "ED"
        obx[3] = ("RTF","Display format in RTF","AUSPDI")
        if ld.has("original_rtf"):
            trtf = ld.original_rtf
        else:
            trtf = rtf.convert_rtf_from_ld(ld.getvalue())
        obx[5] = {0:('ATHEN','ATHEN '+config.version,'L'), # "source" a HD
                  1:"TEXT",
                  2:"RTF",
                  3:"Base64",
                  4:base64.b64encode(bytes(trtf,'us-ascii'))
                  }
    else:
        raise util.AthenError("no such embed file %r" % embed)
    if style == 'ORU':
        msh[8] = ("ORU","R01","ORU_R01")
        msh[11] = ("2.3.1",("AUS","","ISO"),("AS4700.2","","L"))
        orc = {0:'ORC',
               1:'RE', # "observations to follow" table 0119 on pg 293
               3:(ld.get_unique_id(),config.domain,config.domain,'DNS'),
               5:'CM', # order status table 0038 page 303 CM= "order completed"
               12:get_xcn(ld.recipient),
               24:""}
        return [msh,pid,pv1,orc,obr,obx]
    elif style == "REF":
        msh[8] = ("REF","I12","REF_I12")
        msh[11] = ("2.3.1",("AUS","","ISO"),("AS4700.6","","L"))
        rf1 = {0:"RF1",
               1:("A","Accepted","HL70283"), # status
               3:("GRF","General referal","HL70281"), # referral type
               # see table 0281 on pgh 758
               # The Lismore sample uses DRF/discharge referral here, but that's not in the Standard's table, it is in the AU 4700.6 standard pg 20
               # FIXME: scan the message content and apply different types heren as appropriate.
               4:("WR","Send written report","HL70282"), # disposition table 0282 pg 754 Again Lismore use a value DF/Discharge again that's not in the Standard's table, but is in AU 4700.6 pg 21
               5:("O","Outpatient","HL70282"), # category, table 0284 pg 755
               6:(ld.get_unique_id(),ld.get_unique_id()),  # oringating identifer see pg 755. The other optional components refer to the *target* application ID, which we don't know. This is the only required field by 2.3.1 Standard. BUT AHML insit we fill the second component, so use ID again
               11:""
               }
        prd_rp = make_prd(ld.sender)
        prd_rp[1] = [("RP","Referring Provider","HL70286"),("AP","Authoring provider","HL70286")] # table 0286 pg 759 AP is AU extension from the confluence docs, required by them
        prd_rt = make_prd(ld.recipient)
        prd_rt[1] = [("RT","Referred to Provider","HL70286"),("IR","Intended Recipient","HL70286")] # same table, again IR is an AU addition
        return [msh,rf1,prd_rp,prd_rt,pid,obr,obx,pv1] # PV1 at the end is allowed but optional in the Standard, AHML insists, for unclear reasons (all data is elsewhere)
    else:
        util.AthenError("no such style %r" % style)


    
def make_hl7_attachment(segments,style,ld):
    """Turn a list of segments into a MIME attachment
    """
    fname = ld.get_filestub()+'.'+style
    # dummy setup to defeat MIMEApplication's intense desire to use base64
    mt = MIMEApplication('',"edi-hl7")
    del mt['Content-Transfer-Encoding']
    # this let us set exactly what we want
    mt.set_payload(emit.quopri_hl7(emit.emit(segments)))
    mt["Content-Transfer-Encoding"] = "quoted-printable"
    mt['Content-Disposition'] = 'attachment; filename="{}"'.format(fname)
    mt.set_param('name',fname)
    return mt

registry.register_outputter("hl7-oru-ft",lambda ld: make_hl7_attachment(make_hl7("ORU","FT",ld),"ORU",ld),"HL7 - ORU type - plain text")
registry.register_outputter("hl7-oru-rtf",lambda ld: make_hl7_attachment(make_hl7("ORU","RTF",ld),"ORU",ld),"HL7 - ORU type - RTF")
registry.register_outputter("hl7-ref-ft",lambda ld: make_hl7_attachment(make_hl7("REF","FT",ld),"REF",ld),"HL7 - REF type - plain text")
registry.register_outputter("hl7-ref-rtf",lambda ld: make_hl7_attachment(make_hl7("REF","RTF",ld),"REF",ld),"HL7 - REF type - RTF")

