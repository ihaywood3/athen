import json
import time

from twisted.web.resource import Resource
from twisted.web.http import CACHED
from twisted.web.server import NOT_DONE_YET
from twisted.cred.checkers import ANONYMOUS
from twisted.internet.threads import deferToThread
from twisted.logger import Logger

from athen.hub import db, fhir, error, validate

log = Logger()


class FHIRPage(Resource):
    isLeaf = True

    def __init__(self, avatarId):
        if avatarId == ANONYMOUS:
            self.acct = None
        else:
            self.acct = avatarId

    def _send(self, request, doc, default="representation", fixed=False):
        doc = dict(doc)
        if request.args.get(b"_pretty") == [b"1"]:
            indent = 4
        else:
            indent = None
        request.setHeader("Content-Type", "application/fhir+json")
        if "meta" in doc:
            if "lastUpdated" in doc["meta"]:
                v = doc["meta"]["lastUpdated"]
                v = time.mktime(fhir.parse_instant(v))
                if request.setLastModified(v) == CACHED:
                    return
            if "versionId" in doc["meta"]:
                e = 'W/"%d"' % doc["meta"]["versionId"]
                if request.setETag(e) == CACHED:
                    return
        action = default
        if not fixed:
            p = request.getHeader("Prefer")
            if p:
                p = p.split("=")
                if p[0] == "return":
                    action = p[1]
        if action == "minimal":
            return
        elif action == "representation":
            return json.dumps(doc, indent=indent).encode("utf-8")
        elif action == "OperationOutcome":
            if request.method == b"PUT":
                code = "MSG_UPDATED"
                text = "existing resource updated"
            elif request.method == b"DELETE":
                code = "MSG_DELETED_DONE"
                text = "This resource has been deleted"
            elif request.method == b"POST":
                code = "MSG_CREATED"
                text = "New resource created"

            oo = {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "information",
                        "code": "informational",
                        "details": {
                            "text": text,
                            "coding": [
                                {
                                    "system": "http://hl7.org/fhir/ValueSet/operation-outcome",
                                    "code": code,
                                }
                            ],
                        },
                    }
                ],
            }
            return json.dumps(oo, indent=indent).encode("utf-8")

    def render_GET(self, request):
        return self._get(request, False)

    def render_HEAD(self, request):
        return self._get(request, True)

    def _get(self, request, head):
        try:
            if len(request.postpath) == 1:
                if head:
                    raise error.FHIRException(
                        405, "not-supported", "MSG_UNKNOWN_OPERATION"
                    )
                typ = request.postpath[0].decode("ascii")
                return self._search(request, typ)
            elif len(request.postpath) == 2:
                typ = request.postpath[0].decode("ascii")
                id_ = int(request.postpath[1])
                d = db.get_doc(id_)
                v = d.version[d.version.maxKey()]
                if v["resourceType"] != typ:
                    raise error.WrongResourceType()
                if head:
                    return self._send(request, v, "minimal", True)
                else:
                    return self._send(request, v, "representation", True)
            elif len(request.postpath) == 4 and request.postpath[2] == b"_history":
                typ = request.postpath[0].decode("ascii")
                vid = int(request.postpath[3])
                id_ = int(request.postpath[1])
                d = db.get_doc(id_)
                v = d.version[vid]
                if v["resourceType"] != typ:
                    raise error.WrongResourceType()
                if head:
                    return self._send(request, v, "minimal", True)
                else:
                    return self._send(request, v, "representation", True)
            else:
                raise error.NoResource()
        except error.FHIRException as e:
            return self._error(request, e)
        except BaseException as e:
            return self._error(request, error.PythonException(str(e)))

    def _error(self, request, e):
        log.failure("_error")
        request.setHeader("Content-Type", "application/fhir+json")
        request.setResponseCode(e.http_status)
        return json.dumps(e.oo, indent=4).encode("utf-8")

    def _error_async(self, request, e):
        log.failure("_error")
        request.setHeader("Content-Type", "application/fhir+json")
        request.setResponseCode(e.http_status)
        request.write(json.dumps(e.oo, indent=4).encode("utf-8"))
        request.finish()

    def render_POST(self, request):
        try:
            if len(request.postpath) == 2 and request.postpath[1] == b"_search":
                typ = request.postpath[0].decode("ascii")
                return self._search(request, typ)
            elif len(request.postpath) == 1:
                if self.acct is None:
                    raise error.Forbidden()
                typ = request.postpath[0].decode("ascii")
                doc = json.load(request.content)

                if type(doc) is not dict:
                    raise error.JSONException(oo_code="MSG_JSON_OBJECT")
                doc = validate.check_dict(doc)
                if (
                    doc["resourceType"] != typ and typ != "_create"
                ):  # using _create is an extension
                    raise error.WrongResourceType()
                return self._create(request, doc)
            else:
                raise error.NoResource()
        except error.FHIRException as e:
            return self._error(request, e)
        except BaseException as e:
            return self._error(request, error.PythonException(str(e)))

    def _create(self, request, doc):
        db.new_doc(doc, self.acct)
        loc = "%s/%d" % (doc["resourceType"], doc["id"])
        request.setHeader(
            b"Location", b"/" + b"/".join(request.prepath + [loc.encode("ascii")])
        )
        request.setResponseCode(201)
        return self._send(request, doc, "minimal")

    def render_PUT(self, request):
        try:
            if len(request.postpath) == 2:
                if self.acct is None:
                    raise error.Forbidden()
                typ = request.postpath[0].decode("ascii")
                doc = json.load(request.content)
                id_ = int(request.postpath[1])
                if type(doc) is not dict:
                    raise error.JSONException(oo_code="MSG_JSON_OBJECT")
                doc = validate.check_dict(doc)
                if doc["resourceType"] != typ:
                    raise error.WrongResourceType()
                if "id" not in doc:
                    raise error.JSONException("required", "MSG_RESOURCE_ID_MISSING")
                if doc["id"] != id_:
                    raise error.JSONException(
                        "value", oo_code="MSG_RESOURCE_ID_MISMATCH"
                    )
                db.put_doc(doc, self.acct)
                return self._send(request, doc, "minimal")
            else:
                raise error.NoResource()
        except error.FHIRException as e:
            return self._error(request, e)
        except BaseException as e:
            return self._error(request, error.PythonException(str(e)))

    def render_DELETE(self, request):
        try:
            if len(request.postpath) == 2:
                if self.acct is None:
                    raise error.Forbidden()
                typ = request.postpath[0].decode("ascii")
                id_ = int(request.postpath[1])
                v = db.delete_doc(id_, self.acct)
                return self._send(request, v, "minimal")
            else:
                raise error.NoResource()
        except error.FHIRException as e:
            return self._error(request, e)
        except BaseException as e:
            return self._error(request, error.PythonException(str(e)))

    def _search(self, request, typ):
        params = {
            k.decode("utf-8"): [i.decode("utf-8").upper() for i in v]
            for k, v in request.args
        }

        def _writeResult(r):
            base_url = b"/" + b"/".join(request.prepath)
            base_url = base_url.decode("ascii")
            if base_url != "/":
                base_url += "/"
            bundle = {
                "resourceType": "Bundle",
                "type": "searchset",
                "timestamp": fhir.make_instant(),
                "total": len(r),
                "entry": [
                    {
                        "fullUrl": "%s%s/%d" % (base_url, i["resourceType"], i["id"]),
                        "resource": i,
                        "search": {"mode": "match"},
                    }
                    for i in r
                ],
            }
            request.setHeader("Content-Type", "application/fhir+json")
            request.write(json.dumps(bundle).encode("utf-8"))
            request.finish()

        def _resultError(failure, request):
            if failure.check(error.FHIRException):
                self._error(request, failure.value)
            else:
                self._error_async(request, error.PythonException(str(failure.value)))

        d = deferToThread(db.search_doc, params)
        d.addCallback(_writeResult)
        d.addErrback(_resultError, request)
        return NOT_DONE_YET
