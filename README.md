ATHEN
=====

The Autonomous Transport for health: Encrypted Network: NEHTA backwards. An alternative options for the PCEHR that respects privacy, decentralised and easy-to-use.

The Components
--------------

* An LDAP server providing information about doctors and oher health providers and their contact details, including email addresses, GPG key IDs and mailing address. This is the only centralised part of the system however the LDAP server
can be mirrored for redundancy and local use.
* A mailserver (one public one, but unlimited private ones) configured to only use SMTP over TLS. When emails hit the system they are encrypted with GPG to the 
recipients key, if not already. Previously read emails are stored on an encrypted filesystem, which is mounted using the users' password as key, only when the user logs in to check their mail.
* A web interface for reading and writing emails but with medical extensions (such as patient name, address, etc), emails are then translated to HL7 and can be downloaded and imported into existing medical records automatically.
* A web-based downloader for HL7 versions of emails.

Internals
---------

The LDAP directory is a standard OpenLDAP which as public read-only access. It can be used by email clients such as Outlook to find recipients.
The mailserver is postfix, with configuration to insist on TLS for sending and receiving mails. This means some ISPs won't work, but most will, and gmail, hotmail, etc, will all work,
Dovecot IMAP is used to access mails, a Python script is attached to the Linux PAM system, when a user tries to log on, the script mounts the users home directory using their password to decrypt it, and then decrypts any new mails received in the meantime. A cron job runs every 10 minutes to see who is no longer logged on, and unmounts their home directory.
The server does not allow `root' logins. To get root access the administrator can only do this at certain times, late at night (like the time lock on a bank vault), and when this happens all users are logged out and their directories unmounted first.

Why Bother
----------

Email is currently not considered `secure enough' for medical use. There are two main reasons:
* Emails can be read in transit by the ISP or by local network adminstrators (in hopsitals).This is addressed by only using TLS/SSL connections.
* Stored emails can be read by the mailserver administrator, who, even if trusted, can be forced to hand over emails by a Court order (subpnoea). this is addressed by local encrypted of stored emails after receipt.


Weaknesses
----------

Of course whoever has physical access to a mailserver can override all security. However if they power down the machine, or unplug the hard drive, then all the user directories are unmounted and so encrypted, so this is not as easy as it sounds. 
Emails are unencrypted in server RAM, but only ever hit the hard drive on an encrypted state (GPG-encrypted or new mails, filesystem encrypted for the old ones). This means the administrator cannot be forced via a court order to provide emails, as they cannot be read without the users own password.
The only true weakness is if the mailserver is stolen/broekn in to and secretly modified, the new administrator can `lie in wait' for a user to log in, and then grab the password and read all mails. However Australian Courts do not have the power to order an existing administrator to do this.
It does require that you trust the server administrator, however all code is released dopen-source, you are free to run your own server. A [Docker](www.docker.com) image is provided to make this easy. 
 