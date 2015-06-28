FROM ubuntu:14.04
MAINTAINER Ian Haywood <ian@haywood.id.au>

# Add openldap user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN groupadd -r openldap && useradd -r -g openldap openldap
# Install OpenLDAP and ldap-utils
RUN apt-get -y update && \ 
LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get install -y --force-yes --no-install-recommends slapd ldap-utils apache2 python  && \
apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
COPY *.ldif /root/
COPY www/* /var/www/
COPY python/* /usr/lib/cgi-bin/
COPY apache.conf/* /etc/apache2/sites-available/
COPY athen.pem /etc/ssl/certs/
COPY athen.key /etc/ssl/private/
RUN chmod 400 /etc/ssl/private/athen.key
RUN ldapadd -Q -Y EXTERNAL -H ldapi:/// -f /root/athen.ldif
RUN ldapmodify -Q -Y EXTERNAL -H ldapi:/// -f /root/config.ldif
EXPOSE 80 443 389
