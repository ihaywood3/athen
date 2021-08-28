import re

from athen.hub import error


CARD_MULTIPLE = 1
CARD_OPTIONAL = 2
CARD_BOTH = 3

SCHEMATA = {}


def register_schema(typ, **fields):
    SCHEMATA[typ] = fields


def register_schema_func(typ, **fields):
    def reg2(func):
        fields["__func"] = func
        register_schema(typ, fields)
        return func

    return reg2


def check_dict(obj, typ=None):
    s = set(obj.keys())
    if typ is None:
        typ = obj["resourceType"]
        s.remove("resourceType")
    schema = SCHEMATA[typ]
    if "contained" in obj and "__contained" in schema:
        s.remove("contained")
        obj["contained"] = [check_dict(i) for i in obj["contained"]]
    for k, v in schema:
        if not k[:2] == "__":
            card, typ = v
            if k in obj:
                s.remove(k)
                obj[k] = check_scalar(obj[k], card, typ)
            elif card & CARD_OPTIONAL:
                pass
            else:
                raise error.JSONException(
                    "required", diagnostic="required field %s not found" % k
                )
    if len(s) > 0:
        raise error.JSONException(diagnostic="fields not in schema %r" % s)
    if "__func" in schema:
        func = schema["__func"]
        obj = func(obj)
    return obj


def check_scalar(obj, card, typ):
    if card & CARD_MULTIPLE:
        if type(obj) is not list:
            raise error.JSONException("value", diagnostic="expected list, got %r" % obj)
        return [check_scalar(i, 0, typ) for i in obj]
    else:
        if type(typ) is type:
            if type(obj) is not typ:
                if type(obj) is int and typ is float:
                    obj = float(obj)
                else:
                    raise error.JSONException(
                        "value", diagnostic="expected an %r, got %r" % (typ, obj)
                    )
            return obj
        elif type(typ) is str:
            return check_dict(obj, typ)
        elif type(typ) is set:
            if obj in typ:
                return obj
            else:
                raise error.JSONException(
                    "value", diagnostic="%r is not in the set of allowed values" % obj
                )
        elif isinstance(typ, re.Pattern):
            if not typ.match(obj):
                raise error.JSONException(
                    "value",
                    "MSG_BAD_FORMAT",
                    diagnostic="%r does not match required format" % obj,
                )
            return obj
        else:
            raise error.FHIRException(
                500,
                "exception",
                "_broken-schema",
                "unknown type definition %r" % obj,
                "fatal",
            )
