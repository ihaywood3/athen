#!/bin/bash
# special routines for managing GnuPG

set -e

# general generate key and set up
# $1 email $2 real name
function gen_key()
{
    gpg --batch --quiet --no-tty --gen-key 2> /dev/null <<EOF
Key-Type: DSA
Key-Length: 1024
Subkey-Type: ELG-E
Subkey-Length: 1024
Name-Real: $2
Name-Email: $1
Expire-Date: 5y
%no-protection
%no-ask-passphrase
%commit
EOF
    cat > $HOME/.gnupg/gpg.conf <<EOF
trust-model tofu
auto-key-retrieve
tofu-default-policy good
batch
local-user $EMAIL
keyserver keys.gnupg.net
EOF
}

# batch-generate a key must run as relevant user
# expects $USER $HOME $MAILNAME and $FULLNAME set
# emits the fingerprint and then the public key on stdout
function user_gen_key ()
{
    MAILNAME=$(cat /etc/mailname)
    EMAIL=$USER@$MAILNAME
    gen_key $EMAIL "$FULLNAME"
    # now import vmail's key and sign it
    gpg --import -q < ~vmail/pubkey.asc
    gpg --quick-sign -q `cat ~vmail/pubkey.fpr`
    # export our public key to stdout
    gpg -a --export "$EMAIL"
}

# bootstrap vmail's key at server initialisation time
function vmail_gen_key()
{
    export HOME=/home/vmail
    export USER=vmail
    MAILNAME=$(cat /etc/mailname)
    EMAIL=vmail@$MAILNAME
    gen_key $EMAIL "Athen Vmail User on $MAILNAME"
    # now export vmail's key
    gpg -a --export "$EMAIL" > ~/pubkey.asc
    gpg -q --with-colons --with-fingerprint --list-keys "$EMAIL"  | awk -F : '$1 == "pub" { getline; print $10 ; exit }' > ~/pubkey.fpr
}

# to run as vmail, accepts a new user's key on stdin and signs it
function vmail_accept_key()
{
    FPR=$(gpg --homedir /home/vmail/.gnupg -q --with-colons --import --import-options import-show 2> /dev/null | awk -F : '$1 == "pub" { getline; print $10 ; exit }')
    gpg --homedir /home/vmail/.gnupg -q --quick-sign $FPR > /dev/null
}

# accept what comes in on stdin, save it to $2 encrypting for $1
function vmail_encrypt()
{
    HOST=$(cat /etc/mailname)
    gpg -q -r "$1@$HOST" -o $2 --encrypt
}

# decrypt a file on stdin and push to stdout
function mail_decrypt()
{
    gpg -q --decrypt
}

# kill the agent
# $HOME and user id had better be correct
function kill_gpg_agent
{
  gpgconf --kill gpg-agent
}


case "$1" in
gen_key) gen_key $2 $3
;;
user_gen_key) user_gen_key
;;
vmail_accept_key) vmail_accept_key
;;
vmail_gen_key) vmail_gen_key
;;
kill_agent) kill_gpg_agent
;;
esac
