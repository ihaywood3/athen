"""
An emitter for HL7 letters (the REF message type)
"""

from . import emit

import config, util, rtf
import datetime, base64

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
    ("2540","HMAS CRESWELL","ACT"), # cue long and pointless discussion of whether Jervis Bay is technically part of the ACT 
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

def get_xcn(person):
    """Convert the title/firstname/surname dict to an XCN dict"""
    xcn = {1:person['surname'],
           2:person.get("firstname",""),
           5:person.get("title","")
           9:"L"} # Legal name
    if 'provider_number' in person:
        xcn[0] = person['provider_number']
        xcn[8] = "AUSHICPR"
        xcn[12] = "UPIN" # means Yank "universal physician provider number" MO do this



def doc_as_hl7_ft(ld):
    doc = ld.getvalue()
    doc = emit.hl7_escape_special(doc)
    doc = re.sub("[\u2028\u2029]*\uEF05([^\uEF06]+)\uEF06[\u2028\u2029]*",lambda m: "\\.br\\\\H\\"+m.group(1).upper()+"\\.br\\\\N\\",doc)
    doc = re.sub("[\u2028\u2029]*\uEF07([^\uEF08]+)\uEF08[\u2028\u2029]*","\\.br\\\\H\\\\1\\.br\\\\N\\",doc)
    doc = re.sub("[\u2028\u2029]*\uEF09([^\uEF0A]+)\uEF0A[\u2028\u2029]*","\\.br\\\\1\\.br\\",doc)

    doc = re.sub("\uEF02([^\uEF03]+)\uEF03([^\uEF04]+)\uEF04",r"\2 (see \1)",doc)

    doc = doc.replace(BOLD, "\\H\\")
    doc = doc.replace(EBOLD, "\\N\\")
    doc = doc.replace(UND, "\\H\\")
    doc = doc.replace(EUND, "\\N\\")
    doc = doc.replace(PARA,"\\.br\\.br\\")
    doc = doc.replace(LINE,"\\.br\\")
    doc = emit.hl7_escape_non_ascii(doc)
    doc = bytes(doc,'us-ascii','replace')
    return doc

def make_hl7(style,embed,ld=None):
    """
    accept a LogicalDocument and produce an HL7
    Two structures: ORU (i.e. like a path report), and REF (i.e  a "proper" referral)
    Two ways to embed the document: RTF blob (RTF), and HL7 Formatted Text (FT)
    """
    assert ld
    assert style in ['ORU','REF']
    assert embed in ['FT','RTF']
    semail = lo.sender['email']
    temail = lo.recipient['email']
    n = temail.split("@")
    tdomain = n[1]
    run_no,initials = ld.get_run_data()
    m = re.match(r"(.+), ?(.+) ?([0-9]{4})",lo.patient_address)
    if m:
        street = m.group(1)
        town = m.group(2)
        postcode = m.group(3)
        state = _postcode_to_state(postcode,town)
    else:
        street = lo.patient_addrees
        town = ""
        postcode =""
        state = ""
    name = lo.patient_name
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
    msh = {0:"MSH",
           1:b'^~\\&',
           2:('ATHEN','ATHEN '+config.version,'L'),
           3:(semail,config.domain,"DNS"),
           5:(temail,tdomain,"DNS"),
           6:util.now_tz(), 
           8:("ORU","R01"),
           9:ld.get_unique_id(),
           10:"P",
           11:("2.3.1",("AUS","","ISO"),("AS4700.2","","L")),
           15:"AL",
           16:"AUS",
           17:"ASCII",
           20:""  # force correct number of empty fields
           }
    if style == "ref":
        msh[8] = ("REF","I12","REF_I12")
        msh[11] = ("2.3.1",("AUS","","ISO"),("AS4700.6","","L")),
    pid = {0:"PID",
           1:"1",
           # FIXME: standards say PID-3 is required. Have wild samples with it blank .We can only rerally generate fake IDs anyway
           5:(patient_surname,patient_firstname,patient_auxnames,"","","","L")
           7:lo.birthdate,
           8:lo.sex,
           11:(street,"",town,state,postcode,"AUS","C"),
           30:""}
    if style == 'ORU':
        pv1 = {0:"PV1",
               1:"1",
               2;"O", # Outpatient. table 0004 pg 220
               8:get_xcn(ld.recipient),
               9:get_xcn(ld.recipient),
               52:""} # yes 52 frigging fields, even in 2.3.1
        orc = {0;'ORC',
               1;'RE', # "observations to follow" table 0119 on pg 293
               3:(ld.get_unique_id(),config.domain,config.domain,'DNS'),
               5:'CM', # order status table 0038 page 303 CM= "order completed"
               12:get_xcn(ld.recipient),
               24:""}
    elif style == "REF":
        rf1 = {0:"RF1",
               
    obr = {0:'OBR',
           1:"1",
           3:(ld.get_unique_id(),config.domain,config.domain,'DNS'),
           4:("11488-4","Consultation Note","LN"),
           7:ld.get_document_time(),
           16:get_xcn(ld.recipient),
           20:"LN="+ld.get_unique_id(), # black box filed in HL7 official, AU standard has mini-language, page 21 of 2.3.1 4007.2 standards
           22:ld.get_document_time(),
           24:"PHY", # "physician note" used for all letters
           25:"F", # result status "F" = final result table 0123 page 325 2.3.1 Standards
           32:get_xcn(ld.sender),
           45:""}
    obx = {0:"OBX",
           1:"1", # set number - increment for each OBX
           11:"F", # result status  table 85 on page 527
           17:""}
    if embed == "FT":
        obx[3] =("11488-4","Consultation Note","LN")
        obx[2] = "FT"
        obx[5] = doc_as_hl7_ft(ld)
    if embed == "RTF":
        obx[2] = "ED"
        obx[3] = ("RTF","Display format in RTF","AUSPDI")
        if ld.has("original_rtf"):
            trtf = ld.original_rtf
        else:
            trtf = rtf.convert_from_ld(ld.getvalue())
        obx[5] = {0:('ATHEN','ATHEN '+config.version,'L'), # "source" a HD
                  1:"TEXT",
                  2:"RTF",
                  3:"Base64",
                  4:base64.b64encode(trtf)
                  }
