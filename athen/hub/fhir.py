import re
import time
import base64

from athen.hub.validate import register_schema, CARD_OPTIONAL, CARD_MULTIPLE, CARD_BOTH

O = CARD_OPTIONAL
M = CARD_MULTIPLE
B = CARD_BOTH

ID_TYPE = (CARD_OPTIONAL, re.compile("[a-zA-Z0-9\\-\\.]{1,64}"))
EXT_TYPE = (CARD_BOTH, "Extension")

CODE_REGEX = re.compile("[^\\s]+(\\s[^\\s]+)*")
URI_REGEX = re.compile("\\S*")
BASE64_REGEX = re.compile(r"(\s*([0-9a-zA-Z\+\=\\]){4}\s*)+")

register_schema(
    "Coding",
    id=ID_TYPE,
    extension=EXT_TYPE,
    version=(O, str),
    system=(CARD_OPTIONAL, URI_REGEX),
    code=(O, CODE_REGEX),
    display=(O, str),
    userSelected=(O, bool),
)

register_schema(
    "Extension",
    id=ID_TYPE,
    url=(0, re.compile("\\S*")),
    valueString=(O, str),
    valueBase64Binary=(O, BASE64_REGEX),
    # many other types allowed but just these two supported for now
)

register_schema(
    "CodeableConcept",
    id=ID_TYPE,
    extension=EXT_TYPE,
    coding=(B, "Coding"),
    text=(O, str),
)

register_schema(
    "Identifier",
    id=ID_TYPE,
    extension=EXT_TYPE,
    use=(O, {"official", "usual", "temp", "secondary", "old"}),
    type=(O, "CodeableConcept"),
    system=(O, re.compile("\\S*")),
    value=(O, str),
    period=(O, "Period"),
    assigner=(O, "Reference"),
)
x = r"([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])"
x += r"(-(0[1-9]|[1-2][0-9]|3[0-1])(T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)"
x += r"(\.[0-9]+)?(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))?)?)?)?"
DATETIME_REGEX = re.compile(x)
DATE_REGEX = re.compile(
    r"([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)(-(0[1-9]|1[0-2])(-(0[1-9]|[1-2][0-9]|3[0-1]))?)?"
)
TIME_REGEX = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]+)?")


register_schema(
    "Period",
    id=ID_TYPE,
    extension=EXT_TYPE,
    start=(O, DATETIME_REGEX),
    end=(O, DATETIME_REGEX),
)

register_schema(
    "Reference",
    id=ID_TYPE,
    extension=EXT_TYPE,
    reference=(O, str),
    type=(O, re.compile("\\S*")),
    display=(O, str),
    identifier=(O, "Identifier"),
)


INSTANT_REGEX = re.compile(
    r"([0-9]([0-9]([0-9][1-9]|[1-9]0)|[1-9]00)|[1-9]000)-(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])T([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]+)?(Z|(\+|-)((0[0-9]|1[0-3]):[0-5][0-9]|14:00))"
)


def make_instant(t=None):
    if t is None:
        t = time.localtime()
    n = time.strftime("%Y-%m-%dT%H:%M:%S%z", t)
    return "%s:%s" % (n[:-2], n[-2:])


def parse_instant(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    s = s[:-3] + s[-2:]
    return time.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


register_schema(
    "Meta",
    versionId=ID_TYPE,
    lastUpdated=(O, INSTANT_REGEX),
    source=(O, URI_REGEX),
    profile=(B, URI_REGEX),
    security=(B, "Coding"),
    tag=(B, "Coding"),
)

register_schema(
    "Narrative",
    id=ID_TYPE,
    extension=EXT_TYPE,
    div=(0, str),
    status=(0, {"generated", "extensions", "additional", "empty"}),
)

register_schema(
    "HumanName",
    id=ID_TYPE,
    extension=EXT_TYPE,
    use=(O, {"usual", "official", "temp", "anonymous", "nickname", "old", "maiden"}),
    text=(O, str),
    family=(O, str),
    given=(B, str),
    prefix=(B, str),
    suffix=(B, str),
    period=(O, "Period"),
)

register_schema(
    "ContactPoint",
    id=ID_TYPE,
    extension=EXT_TYPE,
    system=(O, {"phone", "fax", "email", "url", "pager", "sms", "other"}),
    value=(O, str),
    use=(O, {"home", "work", "temp", "old", "mobile"}),
    rank=(O, int),
    period=(O, "Period"),
)

register_schema(
    "Address",
    id=ID_TYPE,
    extension=EXT_TYPE,
    use=(O, {"home", "work", "temp", "old", "billing"}),
    type=(O, {"postal", "physical", "both"}),
    text=(O, str),
    line=(B, str),
    city=(O, str),
    district=(O, str),
    state=(O, str),
    postalCode=(O, str),
    country=(O, str),
    period=(O, "Period"),
)

register_schema(
    "Attachment",
    id=ID_TYPE,
    extension=EXT_TYPE,
    contentType=(O, CODE_REGEX),
    language=(O, CODE_REGEX),  # should be set of language codes
    data=(O, BASE64_REGEX),
    url=(O, URI_REGEX),
    size=(O, int),
    hash=(O, BASE64_REGEX),
    title=(O, str),
    creation=(O, DATETIME_REGEX),
)

register_schema(
    "Qualification",
    id=ID_TYPE,
    extension=EXT_TYPE,
    modifierExtension=EXT_TYPE,
    identifier=(B, "Identifier"),
    code=(0, "CodeableConcept"),
    issuer=(O, "Reference"),
    period=(O, "Period"),
)


register_schema(
    "Practitioner",
    id=ID_TYPE,
    extension=EXT_TYPE,
    implicitRules=(O, URI_REGEX),
    language=(O, CODE_REGEX),
    meta=(O, "Meta"),
    modifierExtension=EXT_TYPE,
    text=(O, "Narrative"),
    __contained=True,
    identifier=(B, "Identifier"),
    active=(O, bool),
    name=(B, "HumanName"),
    address=(B, "Address"),
    telecom=(B, "ContactPoint"),
    gender=(O, {"male", "female", "other", "unknown"}),
    birthDate=(O, DATE_REGEX),
    photo=(B, "Attachment"),
    qualification=(B, "Qualification"),
    communication=(B, "CodeableConcept"),
)


register_schema(
    "AvailableTime",
    id=ID_TYPE,
    extension=EXT_TYPE,
    daysOfWeek=(B, {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}),
    allDay=(O, bool),
    availableStartTime=(O, TIME_REGEX),
    availableEndTime=(O, TIME_REGEX),
)


register_schema(
    "NotAvailable",
    id=ID_TYPE,
    extension=EXT_TYPE,
    description=(0, str),
    during=(O, "Period"),
)


register_schema(
    "PractitionerRole",
    id=ID_TYPE,
    extension=EXT_TYPE,
    implicitRules=(O, URI_REGEX),
    language=(O, CODE_REGEX),
    meta=(O, "Meta"),
    modifierExtension=EXT_TYPE,
    text=(O, "Narrative"),
    __contained=True,
    identifier=(B, "Identifier"),
    active=(O, bool),
    period=(O, "Period"),
    practitioner=(O, "Reference"),
    organization=(O, "Reference"),
    code=(B, "CodeableConcept"),
    specialty=(B, "CodeableConcept"),
    telecom=(B, "ContactPoint"),
    availableTime=(B, "AvailableTime"),
    notAvailable=(B, "NotAvailable"),
    # location and healthService not supported
    availabilityExceptions=(O, str),
    endpoint=(B, "Reference"),
)

register_schema(
    "OrgContact",
    id=ID_TYPE,
    extension=EXT_TYPE,
    purpose=(O, "CodeableConcept"),
    name=(O, "HumanName"),
    telecom=(B, "ContactPoint"),
    address=(O, "Address"),
)

register_schema(
    "Organization",
    id=ID_TYPE,
    extension=EXT_TYPE,
    implicitRules=(O, URI_REGEX),
    language=(O, CODE_REGEX),
    meta=(O, "Meta"),
    modifierExtension=EXT_TYPE,
    text=(O, "Narrative"),
    __contained=True,
    identifier=(B, "Identifier"),
    active=(O, bool),
    type=(B, "CodeableConcept"),
    name=(O, str),
    alias=(B, str),
    telecom=(B, "ContactPoint"),
    address=(B, "Address"),
    partOf=(O, "Reference"),
    contact=(B, "OrgContact"),
    endpoint=(B, "Reference"),
)

register_schema(
    "Endpoint",
    id=ID_TYPE,
    extension=EXT_TYPE,
    implicitRules=(O, URI_REGEX),
    language=(O, CODE_REGEX),
    meta=(O, "Meta"),
    modifierExtension=EXT_TYPE,
    text=(O, "Narrative"),
    __contained=True,
    identifier=(B, "Identifier"),
    status=(0, {"active", "suspended", "error", "off", "entered-in-error", "test"}),
    connectionType=(0, "Coding"),
    name=(O, str),
    managingOrganization=(O, "Reference"),
    contact=(B, "ContactPoint"),
    period=(O, "Period"),
    payloadType=(M, "CodeableConcept"),
    payloadMimeType=(B, re.compile(r"[a-z]+/[a-z][a-z0-9\-\.]*")),
    address=(0, URI_REGEX),
    header=(B, str),
)

# convenience functions for managing extensions


def set_ext(d, url, x):
    del_ext(d, url)
    if x is None:
        return
    if "extension" not in d:
        d["extension"] = []
    y = {"url": url}
    # only a subset of spec's values
    if type(x) is bytes:
        y["valueBase64Binary"] = str(base64.b64encode(x), "ascii")
    elif type(x) is str:
        y["valueString"] = x
    elif type(x) is bool:
        y["valueBoolean"] = x
    elif type(x) is int:
        y["valueInteger"] = x
    else:
        raise Exception("unknown type for extension")
    d["extension"].append(y)


def del_ext(d, url):
    if "extension" not in d:
        return
    d["extension"] = [i for i in d["extension"] if i["url"] != url]


def get_ext(d, url):
    if "extension" not in d:
        return None
    for i in d["extension"]:
        if i["url"] == url:
            if "valueString" in i:
                return i["valueString"]
            elif "valueBoolean" in i:
                return i["valueBoolean"]
            elif "valueInteger" in i:
                return i["valueInteger"]
            elif "valueBase64Binary" in i:
                return base64.b64decode(bytes(i["valueBase64Binary"], "ascii"))
    return None


def has_ext(d, url):
    if "extension" not in d:
        return False
    for i in d["extension"]:
        if i["url"] == url:
            return True
    return False


# our extensions

EXT_PGP_KEY = "http://athen.email/extensions/pgp-key"
EXT_VERIFIED = "http://athen.email/extensions/verified"
MAGIC_EXTENSIONS = [EXT_VERIFIED]
