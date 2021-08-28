import datetime
import os
import os.path
import hashlib

import persistent
import attr
from BTrees import IOBTree, OOBTree
import ZODB, ZODB.FileStorage


from athen.hub import fhir, error
from athen.hub.fhir import MAGIC_EXTENSIONS, get_ext, set_ext, del_ext, has_ext


def _get_db():
    if "ATHEN_DB" in os.environ:
        dbpath = os.environ["ATHEN_DB"]
    else:
        dbpath = os.path.expanduser("~/athen.zodb")
    storage = ZODB.FileStorage.FileStorage(dbpath)
    return ZODB.DB(storage)


db = _get_db()

with db.transaction() as c:
    if not hasattr(c.root, "accounts"):
        c.root.accounts = OOBTree.BTree()
    if not hasattr(c.root, "docs"):
        c.root.docs = IOBTree.BTree()
    if not hasattr(c.root, "names"):
        c.root.names = OOBTree.BTree()
    if not hasattr(c.root, "id_count"):
        c.root.id_count = 0


def make_salt():
    return (os.urandom(16), 16, 8, 1)


@attr.s
class Account(persistent.Persistent):
    username = attr.ib()
    password = attr.ib(default=None)
    created = attr.ib(factory=datetime.datetime.now)
    docs = attr.ib(factory=IOBTree.BTree)
    salt = attr.ib(default=None)

    def make_hash(self, password):
        salt, n, r, p = self.salt  # unpack hash parameters
        return hashlib.scrypt(password, salt=salt, n=n, r=r, p=p)

    def set_password(self, password):
        self.salt = make_salt()
        self.password = self.make_hash(password)

    def check_password(self, password):
        return self.password == self.make_hash(password)


@attr.s
class Document(persistent.Persistent):
    version = attr.ib(factory=IOBTree.BTree)
    vid_counter = attr.ib(default=0)
    deleted = attr.ib(default=False)

    def add_doc(self, doc, protect_ext=True):
        if len(self.version) > 0:
            v1 = self.version[self.version.maxKey()]
            if v1["resourceType"] != doc["resourceType"]:
                raise error.WrongResourceType()
            if protect_ext:
                for i in MAGIC_EXTENSIONS:
                    if has_ext(v1, i):
                        set_ext(doc, i, get_ext(v1, i))
                    elif has_ext(doc, i):
                        del_ext(doc, i)
        if "meta" not in doc:
            doc["meta"] = {}
        doc["meta"]["versionId"] = self.vid_counter
        doc["meta"]["lastUpdated"] = fhir.make_instant()
        d = OOBTree.Bucket(doc)
        self.version[self.vid_counter] = d
        self.vid_counter += 1

        return d


def new_doc(doc, acct):
    with db.transaction() as c:
        doc["id"] = c.root.id_count
        c.root.id_count += 1
        d = Document()
        d.add_doc(d)
        c.root.docs[doc["id"]] = d
        c.root.accounts[acct].docs[doc["id"]] = d
    return d


def get_doc(id_):
    with db.transaction() as c:
        try:
            d = c.root.docs[id_]
        except KeyError:
            raise error.NoResource()
    if d.deleted:
        raise error.Deleted()
    return d


def get_user(username):
    with db.transaction() as c:
        return c.root.accounts.get(username)


def set_user(username, new_account):
    with db.transaction() as c:
        c.root.accounts[username] = new_account


def put_doc(doc, acct):
    with db.transaction() as c:
        a = c.root.accounts[acct]
        if doc["id"] not in a.docs:
            # shouldn't this be a 404? no, because the spec allows PUT
            # to create resources, this signals we don't implement it
            raise error.FHIRException(405, "not-supported", "MSG_UNKNOWN_OPERATION")
        d = a.docs[doc["id"]]
        d.deleted = False
        d.add_doc(doc)


def delete_doc(id_, acct):
    with db.transaction() as c:
        a = c.root.accounts[acct]
        if id_ not in a.docs:
            raise error.NoResource()
        d = a.docs[id_]
        d.deleted = True
        v = d.version[d.version.maxKey()]
    return v


class ContinueException(Exception):
    pass


def search_doc(params, typ):
    with db.transaction() as c:
        matches = []
        for i in c.root.docs.values():
            if i.deleted:
                continue
            v = i.version[i.version.maxKey()]
            if v["resourceType"] != typ:
                continue
            if not get_ext(v, fhir.EXT_VERIFIED):
                continue
            if "identifier" in params:
                if "identifier" not in v:
                    continue
                try:
                    for j in params["identifier"]:
                        flag = False
                        for k in v["identifier"]:
                            if id1_match(j, k):
                                flag = True
                        if not flag:
                            raise ContinueException()
                except ContinueException:
                    continue
            if "identifier:of-type" in params:
                if "identifier" not in v:
                    continue
                try:
                    for j in params["identifier:of-type"]:
                        flag = False
                        for k in v["identifier"]:
                            if id2_match(j, k):
                                flag = True
                        if not flag:
                            raise ContinueException()
                except ContinueException:
                    continue
            if "name" in params:
                if typ == "Organization":
                    try:
                        for j in params["name"]:
                            flag = False
                            names = []
                            if "name" in v:
                                names.append(v["name"])
                            if "alias" in v:
                                names.extend(v["alias"])
                            for k in names:
                                if text_match(j, k):
                                    flag = True
                            if not flag:
                                raise ContinueException()
                    except ContinueException:
                        continue
                elif typ == "Practitioner":
                    try:
                        for j in params["name"]:
                            flag = False
                            names = []
                            for k in v["name"]:
                                names.extend(k.get("given", []))
                                names.extend(k.get("suffix", []))
                                names.extend(k.get("prefix", []))
                                if "text" in k:
                                    names.append(k["text"])
                                if "family" in k:
                                    names.append(k["family"])
                            for k in names:
                                if text_match(j, k):
                                    flag = True
                            if not flag:
                                raise ContinueException()
                    except ContinueException:
                        continue
                else:
                    continue
            if "given" in params:
                if typ != "Practitioner":
                    raise error.FHIRException(
                        400,
                        "processing",
                        "MSG_PARAM_UNKNOWN",
                        "search param given can only be used on Practitioner",
                    )
                try:
                    for j in params["given"]:
                        flag = False
                        names = []
                        for k in v["name"]:
                            names.extend(k.get("given", []))
                        for k in names:
                            if text_match(j, k):
                                flag = True
                        if not flag:
                            raise ContinueException()
                except ContinueException:
                    continue
            if "family" in params:
                if typ != "Practitioner":
                    raise error.FHIRException(
                        400,
                        "processing",
                        "MSG_PARAM_UNKNOWN",
                        "search param family can only be used on Practitioner",
                    )
                if len(params["family"]) > 1:
                    raise error.FHIRException(
                        400,
                        "processing",
                        "MSG_PARAM_NO_REPEAT",
                        "family is not allowed to repeat",
                    )
                family = params["family"][0]
                flag = False
                names = []
                for k in v["name"]:
                    if "family" in k:
                        names.append(k["family"])
                for k in names:
                    if text_match(family, k):
                        flag = True
                if not flag:
                    continue
            matches.append(i)
    return matches


def id1_match(param, identifier):
    s = param.split("|")
    if len(s) == 1:
        return param.upper() == identifier["value"].upper()
    elif len(s) == 2:
        return (
            s[1].upper() == identifier["value"].upper()
            and s[0].upper() == identifier.get("system", "").upper()
        )
    else:
        raise error.FHIRException(
            400, "processing", "MSG_PARAM_INVALID", "%r is not valid" % param
        )


def id2_match(param, identifier):
    s = param.split("|")
    if len(s) == 3:
        flag = False
        if "type" not in identifier:
            return False
        if "coding" not in identifier["type"]:
            return False
        for i in identifier["type"]["coding"]:
            if (
                i.get("system", "").upper() == s[0].upper()
                and i.get("code", "").upper() == s[1].upper()
            ):
                flag = True
        return flag and s[2].upper() == identifier["value"].upper()
    elif len(s) == 2:
        # EXTENSION: searching without specifying the system
        flag = False
        if "type" not in identifier:
            return False
        if "coding" not in identifier["type"]:
            return False
        for i in identifier["type"]["coding"]:
            if i.get("code", "").upper() == s[0].upper():
                flag = True
        return flag and s[1].upper() == identifier["value"].upper()
    else:
        raise error.FHIRException(
            400, "processing", "MSG_PARAM_INVALID", "%r is not valid" % param
        )


def text_match(param, data):
    param = param.upper()
    text = text.upper()
    return text.startswith(param)
