ATHEN
=====

The Autonomous Transport for health: Encrypted Network: NEHTA backwards. An alternative option for healthcare communication that respects privacy, decentralised and easy-to-use.

Key Features
--------------

* An [OpenLDAP](http://www.openldap.org/) server as user directory with online registration.
* A mailserver configured to only use SMTP over TLS encryption. Will work with most hospital e-mail systems. When emails hit the system they are encrypted with GPG to the 
recipients key, if not already. Previously read emails are stored on an encrypted filesystem, which is opened using the users' password as key, only when the user logs in to check their mail.
* A Gmail-style web interface for reading and writing emails but with medical extensions (such as patient name, address, etc), emails are then translated to [HL7](http://www.hl7.org/) and can be downloaded and imported into existing medical records automatically.
* An optional downloader for HL7 versions of emails.
* Entirely open-source so multiple servers can exist.

Links
-----

* [the manifesto](manifesto.md) is a non-technical opinion piece about the current state
of communication in Australian healthcare and why this software is an attempt at moving things forward.
* [the whitepaper](whitepaper.md) is a technical outline of how the server works.


