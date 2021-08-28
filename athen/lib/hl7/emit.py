# a very basic HL7 emitter


import datetime
import logging

def emit(segments):
    return bytes("\r".join(_seg(i) for i in segments)+"\r",'us-ascii')

def _seg(segs):
    if type(segs) is list:
        return "|".join(_field1(i) for i in segs)
    elif type(segs) is dict:
        numfields = max(segs.keys())
        output = ["" for _ in range(0,numfields)]
        for k,v in segs:
            output[k] = _field1(v)
        return "|".join(output)
    else:
        raise ValueError

def _field1(f):
    if type(f) is list:
        return "~".join(_field2(i) for i in f)
    else:
        return _field2(f)

def _field2(f):
    if type(f) is tuple or type(f) is list:
        return "^".join(_field3(i) for i in f)
    elif type(f) is dict:
        numsubfields = max(f.keys())
        output = ["" for _ in range(0,numsubfields)]
        for k,v in f:
            output[k] = _field3(v)
        return "^".join(output)
    else:
        return _field3(f)

def _field3(f):
    if type(f) is tuple or type(f) is list:
        return "&".join(_field4(i) for i in f)
    elif type(f) is dict:
        numsubfields = max(f.keys())
        output = ["" for _ in range(0,numsubfields)]
        for k,v in f:
            output[k] = _field4(v)
        return "&".join(output)
    else:
        return _field4(f)

def _field4(f):
    if type(f) is datetime.datetime:
        assert not f.tzinfo is None # we must always be timezone-aware time
        tz = f.tzinfo.utcoffset(f).seconds
        tz_hours  = tz // 3600
        tz_min = (tz % 3600) // 60
        return f.strftime("Y%m%d%H%M%S")+"{:0=+3}{:0>2}".format(tz_hours,tz_min)
    elif type(f) is datetime.date:
        return f.strftime("%Y%m%d")
    elif type(f) is bytes:
        # bytes is our "raw type" that is not escaped
        f = str(f,'us-ascii')
        # but, we escape these two anyway: there is never a reason to leave them in
        f = f.replace("\r","")
        f = f.replace("\n","")
        return f
    elif type(f) is str:
        return hl7_escape_non_ascii(hl7_escape(f))
    else:
        logging.warning("%r is not a string" % f)
        return _field4(str(f))
        
def hl7_escape(f):
    f = f.replace("\\","\\E\\")
    f = f.replace("\r","")
    f = f.replace("\n","")
    f = f.replace("|","\\F\\")
    f = f.replace("^","\\S\\")
    f = f.replace("&","\\T\\")
    return f

def hl7_escape_non_ascii(doc):
    # sadly for HL7 strings we have to go down to ASCII
    # replace most non-ASCII characters seen "in the wild" i.e. from Windows-1252
    # I transliterate German umlauts and es-zett
    # other diacritics I leave alone as I don't know the languages well enough
    # I know stripping them off can change meaning in highly
    # problematic ways (Spanish ano/año the classic  example) so it is better to replace with ?
    
    # first the true Windowsy extensions (not in ISo-8859-1)
    doc = doc.replace("\u20AC","EURO")
    doc = doc.replace("\u2026","...")
    doc = doc.replace("\u2122","TM")
    doc = doc.replace("\u201A",",")
    doc = doc.replace("\u201E",",,")
    doc = doc.replace("\u0160","SZ")
    doc = doc.replace("\u2039","<")
    doc = doc.replace("\u0152","OE")
    doc = doc.replace("\u2018","'") # curly quotes
    doc = doc.replace("\u2019","'")
    doc = doc.replace("\u201C",'"')
    doc = doc.replace("\u201D",'"')
    doc = doc.replace("\u2022","*") # bullet
    doc = doc.replace("\u2013","-")
    doc = doc.replace("\u2014","--")
    doc = doc.replace("\u02DC","~")
    doc = doc.replace("\u0161","sz")
    doc = doc.replace("\u203A",">")
    doc = doc.replace("\u0153","oe")

    # now ISO-8859-1 where it means sense
    doc = doc.replace("\u00A0","_") #   NO-BREAK SPACE
    doc = doc.replace("\u00A1","!") # ¡ INVERTED EXCLAMATION MARK
    doc = doc.replace("\u00A2","c") # ¢ CENT SIGN
    doc = doc.replace("\u00A3","UKP") # £ POUND SIGN
    doc = doc.replace("\u00A4","o") # ¤ CURRENCY SIGN
    doc = doc.replace("\u00A5","yen ") # ¥ YEN SIGN
    doc = doc.replace("\u00A6","|") # ¦ BROKEN BAR
    doc = doc.replace("\u00A7","S") # § SECTION SIGN
    doc = doc.replace("\u00A8","\"") # ¨ DIAERESIS
    doc = doc.replace("\u00A9","(C)") # © COPYRIGHT SIGN
    doc = doc.replace("\u00AA","?") # ª FEMININE ORDINAL INDICATOR
    doc = doc.replace("\u00AB","<<") # « LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
    doc = doc.replace("\u00AC","!") # ¬ NOT SIGN
    doc = doc.replace("\u00AD","") # ­ SOFT HYPHEN
    doc = doc.replace("\u00AE","(R)") # ® REGISTERED SIGN
    doc = doc.replace("\u00AF","-") # ¯ MACRON
    doc = doc.replace("\u00B0","deg") # ° DEGREE SIGN
    doc = doc.replace("\u00B1","+/-") # ± PLUS-MINUS SIGN
    doc = doc.replace("\u00B2","^2") # ² SUPERSCRIPT TWO
    doc = doc.replace("\u00B3","^3") # ³ SUPERSCRIPT THREE
    doc = doc.replace("\u00B4","`") # ´ ACUTE ACCENT
    doc = doc.replace("\u00B5","mu ") # µ MICRO SIGN
    doc = doc.replace("\u00B5g","microgram") # µ MICRO SIGN
    doc = doc.replace("\u00B6","P") # ¶ PILCROW SIGN
    doc = doc.replace("\u00B7",".") # · MIDDLE DOT
    doc = doc.replace("\u00B8",",") # ¸ CEDILLA
    doc = doc.replace("\u00B9","^1") # ¹ SUPERSCRIPT ONE
    doc = doc.replace("\u00BA","?") # º MASCULINE ORDINAL INDICATOR
    doc = doc.replace("\u00BB",">>") # » RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
    doc = doc.replace("\u00BC","1/4") # ¼ VULGAR FRACTION ONE QUARTER
    doc = doc.replace("\u00BD","1/2") # ½ VULGAR FRACTION ONE HALF
    doc = doc.replace("\u00BE","3/4") # ¾ VULGAR FRACTION THREE QUARTERS
    doc = doc.replace("\u00BF","?") # ¿ INVERTED QUESTION MARK
    doc = doc.replace("\u00C4","AE") # Ä LATIN CAPITAL LETTER A WITH DIAERESIS
    doc = doc.replace("\u00C6","AE") # Æ LATIN CAPITAL LETTER AE
    doc = doc.replace("\u00D0","D") # Ð LATIN CAPITAL LETTER ETH
    doc = doc.replace("\u00D6","OE") # Ö LATIN CAPITAL LETTER O WITH DIAERESIS
    doc = doc.replace("\u00D7","*") # × MULTIPLICATION SIGN
    doc = doc.replace("\u00D8","0") # Ø LATIN CAPITAL LETTER O WITH STROKE
    doc = doc.replace("\u00DC","UE") # Ü LATIN CAPITAL LETTER U WITH DIAERESIS
    doc = doc.replace("\u00DE","TH") # Þ LATIN CAPITAL LETTER THORN
    doc = doc.replace("\u00DF","ss") # ß LATIN SMALL LETTER SHARP S
    doc = doc.replace("\u00E4","ae") # ä LATIN SMALL LETTER A WITH DIAERESIS
    doc = doc.replace("\u00E6","ae") # æ LATIN SMALL LETTER AE
    doc = doc.replace("\u00F0","d") # ð LATIN SMALL LETTER ETH
    doc = doc.replace("\u00F6","oe") # ö LATIN SMALL LETTER O WITH DIAERESIS
    doc = doc.replace("\u00F7","/") # ÷ DIVISION SIGN
    doc = doc.replace("\u00FC","ue") # ü LATIN SMALL LETTER U WITH DIAERESIS
    doc = doc.replace("\u00FE","th") # þ LATIN SMALL LETTER THORN

    return doc
