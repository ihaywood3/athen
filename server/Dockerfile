FROM ubuntu:14.04
MAINTAINER Ian Haywood <ian@haywood.id.au>

RUN apt-get -yq update
RUN DEBIAN_FRONTEND=noninteractive apt-get -yqq install supervisor apache2 dovecot-imapd dovecot-ldap libpam-script python-ldap libapache2-mod-php5 php5-ldap php5-common debconf-utils sqlite3 php5-sqlite apache2-utils php-mail-mimedecode inetutils-syslogd lvm2 cryptsetup e2fsprogs openssl
COPY debconf.keys /root/
RUN cat /root/debconf.keys | debconf-set-selections
RUN DEBIAN_FRONTEND=noninteractive apt-get -yqq install postfix postfix-ldap libapache2-mod-nss roundcube roundcube-sqlite3 roundcube-mysql- roundcube-pgsql- 
COPY /etc /etc/
COPY /php /usr/lib/athen/php/
COPY /schema.sql /usr/lib/athen/
COPY /adm /usr/lib/athen/adm/
COPY /python/pam_script_auth /usr/lib/athen/adm/
RUN mkdir /var/lib/roundcube/plugins/athen/
COPY /roundcube/* /var/lib/roundcube/plugins/athen/
# create user vmail, to ensure consistent UID
RUN groupadd -g 1001 vmail ; useradd -g 1001 -m -u 1001 -s /bin/bash vmail
RUN touch /var/mail/vmail ; chown vmail:mail /var/mail/vmail
RUN ln -s /usr/lib/athen/adm/pam_script_auth /usr/share/libpam-script/pam_script_auth
RUN ln -s /usr/lib/athen/adm/pam_script_acct /usr/share/libpam-script/pam_script_acct
RUN /usr/sbin/a2enmod ssl ; /usr/sbin/php5enmod mcrypt ; /usr/sbin/a2ensite default-ssl
RUN cp -f /etc/services /var/spool/postfix/etc/services
RUN cp -f /etc/resolv.conf /var/spool/postfix/etc
EXPOSE 25 80 443 993 587
VOLUME /data
ENTRYPOINT ["/etc/start.sh"]