FROM ubuntu:14.04
MAINTAINER Ian Haywood <ian@haywood.id.au>
RUN apt-get -y update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install supervisor apache2 dovecot-imapd dovecot-ldap libpam-script python-ldap libapache2-mod-php5 php5-ldap php5-common debconf-utils roundcube roundcube-mysql- roundcube-sqlite
COPY debconf.keys /root/
RUN cat /root/debconf.keys | debconf-set-selections
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install postfix postfix-ldap 
COPY /etc /etc/
COPY /adm/* /usr/lib/athen/adm/
COPY /www/* /var/www/
COPY /cgi-bin/* /usr/lib/cgi-bin/
COPY apache.conf/* /etc/apache2/sites-available/
COPY athen.pem /etc/ssl/certs/
COPY athen.key /etc/ssl/private/
RUN chmod 400 /etc/ssl/private/athen.key

EXPOSE 25 80 443 993
CMD ["/usr/bin/supervisord"]