FROM ubuntu:14.04
MAINTAINER Ian Haywood <ian@haywood.id.au>

RUN apt-get -yqq install supervisor apache2 postfix postfix-ldap dovecot-imapd dovecot-ldap roundcube libpam-script python-ldap libapache2-mod-php5 php5-ldap php5-common ssh-server

COPY /etc /
COPY /python /usr/lib/athen/
COPY www/ /var

EXPOSE 22 25 80 443 993
CMD ["/usr/bin/supervisord"]