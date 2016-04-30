#!/bin/sh

#sudo strace -f -eopen /usr/lib/dovecot/deliver -d test <<EOF

/home/ian/athen/server/adm/spool-mail.sh test <<EOF
To: Test User <test@testserver.homenet.org>
From: Ian Haywood <ian@haywood.id.au>
Subject: test message 2
Message-ID: <5719D51E.1060404@internode.on.net>
Date: Fri, 22 Apr 2016 17:39:10 +1000
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 7bit

Test contents 2
EOF
