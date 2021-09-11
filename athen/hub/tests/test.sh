function hub {
    wget -O - --content-on-error --save-headers --http-user=ian --http-password=pass $*
}

function test_crud {
    echo create an organisation
    hub --post-file=org1.json '--header=Prefer:return=OperationOutcome' http://localhost:8080/auth/Organization
    echo fetch it back
    hub http://localhost:8080/auth/Organization/1?_pretty=1
    echo fetch using the public API
    wget -O - --save-headers http://localhost:8080/public/Organization/1?_pretty=1
    echo modify using PUT
    hub --method=PUT --body-file=org1m.json http://localhost:8080/auth/Organization/1?_pretty=1
    echo and check it was modified
    wget -O - --save-headers http://localhost:8080/public/Organization/1?_pretty=1
    echo delete it
    hub --method=DELETE http://localhost:8080/auth/Organization/1?_pretty=1
    echo and check it was deleted  
    wget -O - --save-headers http://localhost:8080/public/Organization/1?_pretty=1
}

function test_create {
    echo create an organisation
    hub --post-file=org1.json  http://localhost:8080/auth/Organization
    echo create practitioners
    hub --post-file=prac1.json http://localhost:8080/auth/Practitioner
    hub --post-file=prac2.json http://localhost:8080/auth/Practitioner
    echo create endpoint
    hub --post-file=endpoint1.json http://localhost:8080/auth/Endpoint
    echo create practitioner role
    hub --post-file=pr1.json http://localhost:8080/auth/PractitionerRole
}

function test_search {
    echo search by name
    hub 'http://localhost:8080/auth/Practitioner?given=I&family=Hay'
    echo search by PN
    hub 'http://localhost:8080/auth/PractitionerRole?identifier:of-type=UPIN|246564PJ'
    echo search by AHPRA
    hub 'http://localhost:8080/auth/Practitioner?identifier:of-type=AHPRA|MED123456'
    echo search organisation
    hub 'http://localhost:8080/auth/Organization?name=Ninox&_pretty=1'
}

test_search
