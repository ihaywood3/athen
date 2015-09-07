FROM ubuntu:14.04
MAINTAINER Ian Haywood <ian@haywood.id.au>

RUN apt-get -yq update
RUN DEBIAN_FRONTEND=noninteractive apt-get -yqq install supervisor apache2 dovecot-imapd dovecot-ldap libpam-script python-ldap libapache2-mod-php5 php5-ldap php5-common debconf-utils postgresql
COPY debconf.keys /root/
RUN cat /root/debconf.keys | debconf-set-selections
RUN DEBIAN_FRONTEND=noninteractive apt-get -yqq install postfix postfix-ldap libapache2-mod-nss
RUN su postgres -c "/usr/lib/postgresql/9.3/bin/pg_ctl start -D /etc/postgresql/9.3/main/" && \
    DEBIAN_FRONTEND=noninteractive apt-get -yqq install roundcube roundcube-pgsql roundcube-mysql-  && \
    su postgres -c "/usr/lib/postgresql/9.3/bin/pg_ctl stop -D /etc/postgresql/9.3/main/"
COPY /etc /etc/
COPY /python /usr/lib/athen/python/
# TEMP: create user vmail
RUN useradd -m -p test -s /bin/bash vmail
RUN touch /var/mail/vmail
RUN chown vmail:mail /var/mail/vmail
RUN ln -s /usr/lib/athen/python/pam_script_auth /usr/share/libpam-script/pam_script_auth
RUN ln -s /usr/lib/athen/python/pam_script_acct /usr/share/libpam-script/pam_script_acct
RUN /usr/sbin/a2enmod ssl
RUN /usr/sbin/php5enmod mcrypt
RUN /usr/sbin/a2ensite default-ssl
EXPOSE 25 80 443 993
ENTRYPOINT ["/usr/bin/supervisord"]