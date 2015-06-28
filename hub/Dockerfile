FROM ubuntu:14.04
MAINTAINER Ian Haywood <ian@haywood.id.au>

# Add openldap user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN groupadd -r openldap && useradd -r -g openldap openldap
# Install OpenLDAP and ldap-utils
RUN apt-get -y update && \ 
LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get install -y --force-yes --no-install-recommends slapd ldap-utils apache2 python  && \
apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
COPY *.ldif /var/lib/ldap/
RUN su openldap -c "/usr/sbin/slapadd -n 0 -l /var/lib/ldap/athen.ldif"
RUN /usr/sbin/slapd -h 'ldap:/// ldapi:///' -g openldap -u openldap -F /etc/ldap/slapd.d/ && /usr/bin/ldapmodify -Q -Y EXTERNAL -H ldapi:/// -f /var/lib/ldap/config.ldif && killall slapd && sleep 5
RUN su openldap -c "/usr/sbin/slapadd -n 1 -l /var/lib/ldap/base.ldif"
EXPOSE 389
ENTRYPOINT /usr/sbin/slapd -h 'ldap:/// ldapi:///' -g openldap -u openldap -F /etc/ldap/slapd.d/ -d 0
#ENTRYPOINT /bin/bash