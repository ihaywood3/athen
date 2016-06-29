#!/bin/bash
# special routines for managing GnuPG

set -e

# batch-generate a key
# $1=username $2=real name
function gen_key ()
{
    HOST=$(cat /etc/mailname)
    UHOME=/home/athen/home/$1
    EMAIL=$1@$HOST
    su $1 -c "gpg --batch --gen-key --homedir $UHOME" <<EOF
Key-Type: DSA
Key-Length: 1024
Subkey-Type: ELG-E
Subkey-Length: 1024
Name-Real: $2
Name-Email: $EMAIL
Expire-Date: 5y
%no-protection
%no-ask-passphrase
%commit
EOF
    gpg --homedir $UHOME --export $EMAIL | gpg --import
    KEYID=$(gpg --with-colons --homedir $UHOME --list-public-keys $EMAIL | awk -F : '$1 == "pub" { print $5}')
    cat $KEYID > $UHOME/keyid.txt
    chown $1:vmail keyid.txt
    #gpg --keyserver athen.mail --send-keys $KEYID
}

