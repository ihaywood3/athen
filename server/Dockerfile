FROM ubuntu:14.04
MAINTAINER Ian Haywood <ian@haywood.id.au>

RUN apt-get -yq update
RUN DEBIAN_FRONTEND=noninteractive apt-get -yqq install supervisor apache2 dovecot-imapd dovecot-ldap libpam-script python-ldap libapache2-mod-php5 php5-ldap php5-common debconf-utils postgresql
COPY debconf.keys /root/
RUN cat /root/debconf.keys | debconf-set-selections
RUN DEBIAN_FRONTEND=noninteractive apt-get -yqq install postfix postfix-ldap 
RUN su postgres -c "/usr/lib/postgresql/9.3/bin/pg_ctl start -D /etc/postgresql/9.3/main/" && \
    DEBIAN_FRONTEND=noninteractive apt-get -yqq install roundcube roundcube-pgsql roundcube-mysql-  && \
    su postgres -c "/usr/lib/postgresql/9.3/bin/pg_ctl stop -D /etc/postgresql/9.3/main/"
COPY /etc /etc/
COPY /python /usr/lib/athen/python/

EXPOSE 22 25 80 443 993
ENTRYPOINT ["/bin/bash"]