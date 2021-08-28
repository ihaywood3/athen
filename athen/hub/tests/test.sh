function hub {
    wget -O - --content-on-error --save-headers --http-user=ian --http-password=pass $*
}

echo create an organisation
hub --post-file=org1.json http://localhost:8080/auth/Organization
echo fetch it back
hub http://localhost:8080/auth/Organization/1?_pretty=1
echo fetcn using the public API
wget -O - --save-headers http://localhost:8080/public/Organization/1?_pretty=1
