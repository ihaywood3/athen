class FHIRException(Exception):
    def __init__(
        self, http_status, issue_type, oo_code=None, diagnostic=None, severity="error"
    ):
        self.http_status = http_status
        issue = {"severity": severity, "code": issue_type}
        if oo_code:
            if oo_code.startswith("_"):
                oo_code = oo_code[1:]
                url = "http://athen.email/operation-outcome-extension-codes"
            else:
                url = "http://hl7.org/fhir/ValueSet/operation-outcome"
            issue["details"] = {"coding": [{"system": url, "code": oo_code}]}
        if diagnostic:
            issue["diagnostics"] = diagnostic
        self.oo = {"resourceType": "OperationOutcome", "issue": [issue]}


class PythonException(FHIRException):
    def __init__(self, m):
        FHIRException.__init__(self, 500, "exception", "_python", m, "fatal")


class WrongResourceType(FHIRException):
    def __init__(self):
        FHIRException.__init__(self, 400, "value", "MSG_RESOURCE_TYPE_MISMATCH")


class NoResource(FHIRException):
    def __init__(self):
        FHIRException.__init__(self, 404, "not-found", "MSG_NO_EXIST")


class Forbidden(FHIRException):
    def __init__(self):
        FHIRException.__init__(self, 403, "forbidden", "MSG_AUTH_REQUIRED")


class Deleted(FHIRException):
    def __init__(self):
        FHIRException.__init__(self, 412, "deleted", "MSG_DELETED")


class JSONException(FHIRException):
    def __init__(
        self, issue_type="invariant", oo_code="MSG_ERROR_PARSING", diagnostic=None
    ):
        FHIRException.__init__(
            self,
            400,
            issue_type,
            oo_code,
            diagnostic,
        )
