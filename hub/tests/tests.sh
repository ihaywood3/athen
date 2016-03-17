#!/bin/bash
set +x

# basic test function
wget_server()
{
    wget --post-data=$1 -O - \
      --certificate=cert.pem --private-key=key.pem \
      --no-check-certificate \
      https://127.0.0.1/api || true
}

# unit tests for ATHEN hub server

echo create a new organisation: but name exists
wget_server 'type=org&action=create&o=Test%20Organisation&st=1%20Foo%20St&l=Mornington&postalCode=3111&userPassword=foobar&businesscategory=General%20Practice'

echo  create new org different name: should work
wget_server 'type=org&action=create&o=Test%20Organisation%202&st=1%20Foo%20St&l=Mornington&postalCode=3111&userPassword=foobar&businesscategory=General%20Practice'

echo  create new org: invalid data
wget_server 'type=org&action=create&o=Test%20Organisation%204&st=1%20Foo%20St&l=Mornington&postalCode=31AB&userPassword=foobar&businesscategory=General%20Practice' 

echo Edit existing organisation
wget_server 'type=org&action=edit&o=Test%20Organisation%202&st=2%20Foo%20St'

echo Edit non-existing organisaton: should fail
wget_server 'type=org&action=edit&o=Test%20Organisation%203&st=2%20Foo%20St'

echo Add a user to an organisation
wget_server 'type=user&action=create&o=Test%20Organisation%202&sn=Haywood&givenname=Ian&medicalSpecialty=psychiatrist&providerNumber=246564PJ'

echo edit a user
wget_server 'type=user&action=edit&o=Test%20Organisation%202&cn=Ian%20Haywood&providerNumber=246564QX'

echo confirm an organisation: should fail value wrong
wget_server 'type=org&action=confirm&o=Test%20Organisation%202&nonce=ABCDEF123'
