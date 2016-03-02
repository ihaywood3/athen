FROM ubuntu:14.04
MAINTAINER Ian Haywood <ian@haywood.id.au>

# Add openldap user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN groupadd -r openldap && useradd -r -g openldap openldap
# Install OpenLDAP and ldap-utils
RUN apt-get -y update && \ 
 LC_ALL=C DEBIAN_FRONTEND=noninteractive apt-get install -y --force-yes --no-install-recommends slapd ldap-utils apache2 python supervisor texlive-latex-base cups-client python-m2crypto python-ldap python-flask && \
 apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
COPY *.ldif /var/lib/ldap/
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
RUN mkdir -p /var/lock/apache2 /var/run/apache2 /var/run/sshd /var/log/supervisor
RUN su openldap -c "/usr/sbin/slapadd -n 0 -l /var/lib/ldap/athen.ldif"
RUN /usr/sbin/slapd -h 'ldap:/// ldapi:///' -g openldap -u openldap -F /etc/ldap/slapd.d/ && /usr/bin/ldapmodify -Q -Y EXTERNAL -H ldapi:/// -f /var/lib/ldap/config.ldif && killall slapd && sleep 5
RUN su openldap -c "/usr/sbin/slapadd -n 1 -l /var/lib/ldap/base.ldif"
COPY python/* /usr/lib/cgi-bin/
COPY apache.conf/ /etc/apache2/sites-available/
COPY client.conf /etc/cups/
COPY athen.pem /etc/ssl/certs/
COPY athen.key /etc/ssl/private/
RUN chmod 400 /etc/ssl/private/athen.key
EXPOSE 80 389 443
CMD ["/usr/bin/supervisord"]
#ENTRYPOINT /bin/bash
