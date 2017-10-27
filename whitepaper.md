ATHEN The System
================

Origins
-------

The very original germ was a proposal by Tim Churches on the GPCG-TALK e-mail list about 10-12
years ago (I don't have archives that far back). His proposal was called JOG: Jabber, OpenLDAP, GnuPG.
It would have worked more like Medical-Objects does now: native clients on each user system that
exchange HL7 messages, encrypted end-to-end with GnuPG and moved via Jabber.

ATHEN swaps Jabber for SMTP, but uses OpenLDAP largely in the way Tim envisioned.
The schema file [athen.schema](athen/hub/athen/schema) was originally called `jog.schema`

Next was the Wedgetail Project that I worked on with David Guest, Tony Lembke and others around 7--8 years ago.
It was different again, being more of a shared health-record than a messaging system. But it
introduced to me the concept that web-based systems could work. The concept of
'provisional' and 'confirmed' users and snail-mailing confirmation letters comes from Wedgetail.

I should also quote here the "Guest criteria": David Guest's formulation for what
a electronic messaging system would need to be to go beyond the current GP<->pathologist axis.

1. Free at point of use
2. Can be operated by clerical staff
2. Requires no special software to be installed at the user end.
3. Allows data import into Medical Director and similar programs

ATHEN aims to be a system that can fulfil the Guest criteria, as close as possible.

David Guest also wrote a PIT file generator, [PITifil](http://ozdoc.mine.nu/pitifil/),
which is another inspiration. Think of ATHEN as PITifil on thw web, on steroids (and LSD).

Components
----------

Note: the acronym EMR refers to "electronic medical record": Medical Director/Best Practice/Zedmed etc.

ATHEN is a Linux Ubuntu server largely running off-the-shelf software:
1. [OpenLDAP](http://www.openldap.org/) for the user directory using a custom extension schema. The standard schema is also
used so the directory can be used by other mail clients.
1. [Postfix](http://www.postfix.org/) for SMTP mail
2. [Dovecot](http://www.dovecot.org/)  for IMAP mailboxes
3. [LUKS](https://gitlab.com/cryptsetup/cryptsetup/blob/master/README.md) to encrypt each user's home directory (including their mail spools). GnuPG for encrypting mails received when the home directory isn't mounted.
4. Apache2 and PHP using [Roundcube](https://roundcube.net/) for Webmail interface.
5. The registration and maintenance interface is in python using [Flask](http://flask.pocoo.org/), however it has no SQL backend: all user data goes in the LDAP directory.

Receiving Mail Run-Through
--------------------------

1. Mail hits Postfix on port 25 (STARTTLS is compulsory)
2. Passed to athen/server/adm/spool-mail.sh. Checks if the user
is logged in, if so skip to 7., if not
3. mail is encrypted with the user's public key using GnuPG and saved under /home/vmail/spool/
Note no e-mail processing is done here, it's saved without examination.
4. User logs in (usually via Dovecot IMAP). Via Linux
PAM system athen/server/adm/pam_script_auth is run
5. User home directory is mounted with the user's password as the LUKS
encryption key. See python/server/adm/cryptoloop.sh
6. Calls athen/server/adm/unspool-mail.sh to cycle through the
mails spooled at (3) above.
7. Each user has a tiny [compiled program](athen/server/user-shim.c) in their home directory 
which is setuid and owned by that user, so calling it changes the UID to that user.
8. mail is passed to athen/server/python/deliver.py
9. Now with the home directory mounted we can access the private key and decrypt with GnuPG..
10. Headers are recorded by athen/server/python/accounting.py in the user's audit database
(see athen/lib/userdb.py). This is a SQLite datebase in each user's home directory.
If the mail is actually an acknowledgment or a read receipt, this is logged against the original sent mail.
Read receipts that are successfully parsed don't proceed further.
11. The mail is examined by athen/lib/mailfilter.py to see if it is suitable for conversion. Users that don't have an EMR
can elect to always skip this step and go to 16.
11. Converter plugins register in athen/lib/registry.py, currently HTML and plain text are the only ones. [FUTURE]: at
least RTF and Microsft Word .DOC, possibly more.
12. Conversion writes text to an object of LogicalDocument class (see athen/lib/registry.py)
13. Users nominate their preferred delivery format, this is stored in OpenLDAP as the `deliveryFormat`
field. Currently options are PIT (athen/lib/pit.py) and HL7, both REF and ORU messages types can be
generated (athen/lib/hl7/letter.py)
14. IF conversion isn't possible any of the conversion plugins raise `registry.NotPossible` exception,
delivery continues as normal but no conversion occurs.
15. If conversion is successful, the new HL7/PIT file is added as an attachment and the e-mail proceeds...
16. to Dovecot for saving into the usual mail spool (in a 'normal' mail system it would jump from 1. straight to here, Dovecot being called by Postfix directly)
17. the user can view the mail and download (if desired) the attachment via Roundcube for import into the EMR. They can view
the SQLite-based audit log for any message via Roundcube plugins (athen/server/roundcube/viewlog.js)
18. Every hour crom calls athen/server/adm/umount-all.sh: any user with no active process (again usually
Dovecout imapd) has their home directory unmounted. `unmount-all.sh` is also run
automatically whenever the administrator logs in, so the adminstrator can't spy on users you have their home directory available.

Sending Mail Run-Through
------------------------

1. Mail is composed in Roundcube, user can type in patient metadata (name, DOB, etc)
using the [Roundcube extension](athen/server/roundcube/athen.js). This is encoded in the Subject line of the mail.
2. Mail hits postfix on the 'submission' interface (port 587) and passed to
athen/server/python/outgoing.py. 
3. all mails get a Dispositon-Notifcation-To header (a request for a read-receipt)
if the e-mail client didn't add one.
4. [FUTURE] if patient metadata isn't in the Subject, scan for an attachment (presumably RTF), which we
can parse for patient data. Presumably these are templates we provide for use in Medical Director/Best Practice etc.
With this there is no requirment to use Roundcube, any mail client (Thunderbird, Outlook, etc) can work and
submit mail directly at step 2. above
5. [FUTURE] Look to see if the recipient has a GnuPG key published somewhere and encrypt using that
6. Send using Postfix and STARTTLS.
7. Read receipts and delivery status notifcations (DSNs) are received and logged back to the user's SQLite audit log
(athen/lib/userdb.py)
8. User can look at the audit log for each sent message via Roundcube 

New User Run-Through
--------------------

1. athen/server/python/server.py is a Flask-based web application.
2. User fills in the form and submits. Users can be an 'organisation' (i.e. one e-mail account for the whole
organisation). Employees can be listed beneath the organisation entry in LDAP, but this is simply to help
people find the organisation's contact via a individuals name or provider number, those employees can't log in in their own right.
I expect GPs and larger allied health  practices to use this mode.
Conversely there is an 'individual' mode, this is for solo specialists/allied health, and hospital doctors whose employer can't/won't provide a
 workable messaging system.
2. server.py talks to the OpenLDAP server and saves the user data. the account is flagged as 'provisionally' registered
3. server.py uses athen/server/python/control.py to access the Bash script athen/server/adm/server.sh,
which is running as root (the python Flask code isn't root and can't do any system admin stuff itself)
4. server.sh calls athen/server/make-home.sh which sets up the encrypted home directory as a loopback file,
generates the GnuPG private/public keypair and other setup.
5. back in server.py it calls LaTeX using a template to compose a welcome letter.
6. Currently me (the admin) checks the `latex_output` directory, prints off the welcome letters and sticks them in the post.
Hopefully this will become unmanageable and I will have to shift to a commerical mailing company with a web API (several exist already)
7. User gets their welcome letter and enters the confirmation code (see athen/server/python/server.py function 'confirm')
and becomes 'confirmed' on LDAP,

Currently there is no difference between what 'confirmed' and 'provisional' users can do, I'm open to ideas about
this: restricting sending or receiving. Certainly if an account stays unconfirmed for more than 2-3 weeks questions
will be asked and eventually the account deleted.

Download Run-Through
--------------------

As proof-of-concept I have written  downloader, a la the pathologist's Fetch (see athen/windows). It is
written in PowerShell and would be provided as an installable program (again like Fetch/Medical-Objects/Argus/etc)

1. PowerShell script is run every hour from Windows Scheduled Tasks
2. uses ssh to log on to the ATHEN server
3. calls athen/server/python/list-emails-download.py. This script scans the inbox and saves attachments to
a donwload/ directory in the user's home directory.
4. ssh scp is used to download each file. 
5. athen/server/python/report-file-download.py is used to report back that files are downloaded (this is saved to the audit log)
The e-mail is moved from the IMAP Inbox to the Downloaded folder.
6. When run again the script watches to see if the file has been deleted, and reports back when it has ('confirming' the
target medical records program has done something with the file). report-file-download.py then sends a delivery status notifcation back to the
original sender, if they are on ATHEN too, it gets recorded in their audit log. 

Note there is no expectation all GP users install the downloader in the first instance: the web interface is the main game. Only
if users with an EMR find they get large number of messages which can import, they can install it as a conviennce,

The downloader isn't properly tested or really finished.

It would be trivial to write a downloader as a Bash script to run on Linux/MacOS.

Is Sending Letters Good Enough?
------------------------------

This is a tricky point and bears a bit of thought beyond "no, we need more security!". NEHTA/ADMA certificates
require certified copies of 100-points of ID, in practice from at least two people in every organisation (usually one clinician and one clerical staff). Experience shows this is "too hard"
and take up is very low outside of GPs forced to do it by ePIP.

Conversely pure online signup (like Google/Facebook/WhatsApp) clearly isn't good enough, geo-locating via IP address doesn't help. I think a snail mail reply
offers reasonable confirmation the online user at least can read paper mail at the organisation they claim to work for. If unauthorised people
can read your paper letters, you have bigger problems than a fake ATHEN account in your name. I think letters provide the right balance betwen security and
something that's easy enough to actually get used.

Work Plan
---------

This is the one NEHTA style buzzword I am going to use.

1. Writing the core system as proof-of-concept

2. Progressively opening up for comment, first to those I trust, then more publicly, and modifying as required.

3. Encouraging people to use a test server and report bugs and problems. Sample HL7 and PIT files
are provided and by experimentation finding what formats work for what EMRs 
 Obviously this step
requires interested beta-testers with an EMR, if these people don't come forward, the system stays as a
"secure" but otherwise fairly plain webmail system.

4. Working on a system for getting letters 'out' of GP systems without having to manually
key in the patient name/DOB fields in the web interface. Presuambly this will
work by parsing RTFs based on a template, but again active involvement from
people running EMRs is required to develop this.

4. Going live with some advertising, probably in Pulse+IT and the various medical rags (Medical Observer, OzDoc etc)

5. More work on the Windows downloader if there is interest.

6. Suppporting other parties to run copies of the ATHEN server (see athen/INSTALL.md) -- but installation
will always require comfort with the Linux command line, There's never going to be a "point-and-click" version
of the server for Windows: because to work as a mailserver it needs a static IP address, reverse DNS set correctly,
and various ports open, etc. The "I don't do command line" crowd aren't interested in that either.

Each server can maintain their own user LDAP directory, and LDAP replication is used to share directory
information betwen servers.