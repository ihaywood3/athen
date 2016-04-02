#!/bin/bash
set +x

# basic test function
wget_server()
{
    wget --post-data=$1 -O - \
      --certificate=cert.pem --private-key=key.pem \
      --no-check-certificate \
      https://127.0.0.1:5000/api || true
}

# unit tests for ATHEN hub server

echo create a new organisation: but name exists
wget_server 'type=org&mode=new&o=Test%20Organisation&street=1%20Foo%20St&st=Victoria&l=Mornington&postalCode=3111&mail=test%40athen.net.au&businessCategory=General%20Practice'

echo  create new org different name: should work
wget_server 'type=org&mode=new&o=Test%20Organisation%202&street=1%20Foo%20St&st=Victoria&l=Mornington&postalCode=3111&mail=test%40athen.net.au&userPassword=foobar&businessCategory=General%20Practice'

echo  create new org: invalid data
wget_server 'type=org&mode=new&o=Test%20Organisation%204&street=1%20Foo%20St&st=Victoria&l=Mornington&postalCode=31AB&mail=test%40athen.net.au&userPassword=foobar&businessCategory=General%20Practice' 

echo Edit existing organisation
wget_server 'type=org&mode=edit&o=Test%20Organisation%202&st=2%20Foo%20St'

echo Edit non-existing organisaton: should fail
wget_server 'type=org&mode=new&o=Test%20Organisation%203&st=2%20Foo%20St'

echo Add a user to an organisation
wget_server 'type=user&mode=new&o=Test%20Organisation%202&sn=Haywood&givenName=Ian&medicalSpecialty=psychiatrist&mail=test2%40athen.net.au&providerNumber=246564PJ'

echo edit a user
wget_server 'type=user&mode=edit&o=Test%20Organisation%202&sn=Haywood&givenName=Ian&providerNumber=246564QX'

#echo confirm an organisation: should fail as nonce value wrong
#wget_server 'type=org&mode=confirm&o=Test%20Organisation%202&nonce=ABCDEF123'

# delete our LDAP entries to restore db status
ldapdelete -x -D "cn=admin,dc=athen,dc=net,dc=au" -w denethor 'cn=Ian Haywood,o=Test Organisation 2,mxDomain=haywood.id.au,dc=athen,dc=net,dc=au' 
ldapdelete -x -D "cn=admin,dc=athen,dc=net,dc=au" -w denethor 'o=Test Organisation 2,mxDomain=haywood.id.au,dc=athen,dc=net,dc=au'
#ldapdelete -x -D "cn=admin,dc=athen,dc=net,dc=au" -w denethor 'mxDomain=haywood.id.au,dc=athen,dc=net,dc=au' 
