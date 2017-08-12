
Clinical Messaging in Australia
================================

Taking the 10,000ft view, there are four ways
health practitioners and organisations can send messages to each other in Australia.

1. Paper letters.
2. Fax. Fax transmission is an official [standard](http://www.itu.int/rec/T-REC-T.30/en) so
by this I mean that a fax machine made by, say, HP can work seamlessly
with fax machines from other companies (Canon, Kyocera, etc)
3. Email, by this I mean transmissions based on the [SMTP standard](https://tools.ietf.org/html/rfc821) and its
various extensions. Again it is "open": anyone with the technical ability to run a mailserver
can intercommunicate with any other.
4. Several commercial messaging products. This began with the pathology companies who provided (and still do) their own programs
such as Fetch to transmit pathology reports with secure encryption. Now the 3 most common for general messaging are Argus (now a division of Telstra), 
[Medical-Objects](https://www.medical-objects.com.au/), and [HealthLink](http://www.healthlink.net). Hereafter
I refer to them as ``the vendors''. 

    Crucially, unlike the other 3 technologies vendors do *not* use a standard and cannot interoperate with
    each other: Argus users cannot message Medical-Objects users, etc.
	[Encouragement](https://www.digitalhealth.gov.au/get-started-with-digital-health/what-is-digital-health/secure-messaging)
	from the regulator
    (the "Australian Digital Health Agency") to use a standard has not changed this problem.

All four methods are in widespread use and there is general agreement this
isn't an ideal state of affairs.

Furthermore, this arrangment can't last, post and fax are on an inevitable decline
forcing a choice between 3. and 4. For the past years a clear bifurcation has been emerging: GPs rarely use e-mail
on the grounds of security, yet despite this all other health sectors are using it more at the 
expense of the other three methods.

Consequently communication with GPs is mainly
by fax, being still the highest technology in common.
This could be potentially bad for general practice, GPs risk being "punished for
doing the right thing": isolated from the rest of the health system because they
won't compromise on messaging security.

Message Security
---------------

The security problems of any messaging system fit into 4 categories. Systems are
not "secure" or "insecure" as a binary property, but exist on a continuum in terms of how they address them.

1.  Identity security: the ability to know the message is going to
the right person. We trust posties give the letter to the address
written on the letter, for example.

2.  Storage security, the lock on the mailbox. Fax machines don't have a lock, but are seen as safe-ish because the fax machine
is inside the office: a printed fax sitting on the tray is no more or less secure than all the other bits
of paper lying around.

3.  Payload security: people sending you "bad stuff" like advertising, scams and viruses.

4.  Transport security, the envelope. Encryption plays this role for electronic communications.

The Division: Hospitals
-----------------------

The main recent change I have seen in the last 2--3 years is the staff of local public hospitals have 'blinked' and started
e-mailing, unencrypted, clinical documents in a range of contexts, this is apparent both as a doctor and (now more recently) as a patient
of that system. They are not doing it automatically: if I wanted a discharge summary, for example, I or my secretary had to ask
a human (usually an allied health clinician in the target department) to manually email it to me, but it is happening.

Medicare have also 'blinked' on the issue:
by 2015 I started receiving referrals from paediatricians via e-mail, and this
was acceptable for Medicare billing at the consultant rate.

Lot of other organisations in and around health have been routinely using e-mail for some time: schools, NGO charities,
Child Protection (known as "DOCS" in most other States), police, allied
health, psychologists, etc, etc.

I suspect the main reason is for this shift is hospitals and other large organisations have for some time run 
(or commissioned an IT firm to run for them) their own SMTP mailservers. This has allowed them to manage *some*
of the security issues above:

1.  They can make the e-mail address reflect the legal name of the individual and their employer. For example
    as a registrar at Austin Hospital my e-mail was `Ian.Haywood@austin.org.au`. This fixes the identity
    security problem (at least for receiving),
    and;

2.  Brings storage security under their control: like the fax machine it's now "inside the office"

3.  With control of the server organisations have gained more confidence in mitigating 
    payload attacks via viruses and trojans: using hospital e-mail for many years I found spam and viruses
    were quite rare.

None of this addresses the transmission security issue, of course, e-mails still leave and enter
the hospital network unencrypted.


The Division: GPs
-----------------

The main proximate reason is they are "not allowed": GPs remain under [formal advice](http://www.racgp.org.au/your-practice/ehealth/protecting-information/email/) 
e-mail is not secure
enough. Many GPs assume this is "the law" and binding across the sector, but this is simply wrong:
Child Protection and the Victorian coroner's
office have sent me highly sensitive reports about adolescent suicides by unencrypted e-mail, therefore it's legal.
(if not, from an IT perspective, a particularly wise thing to do!)

It's important to note here that the rest of the health sector doesn't have accreditation
as GPs understand it: private specialists have resisted the concept, and hospital accreditation works exclusively with admin around management processes: 
it's not as if there is a guy with a clipboard stalking the wards and quizzing interns how 
they securely communicate with GPs. So there is no-one to tell the other sectors of the health system e-mail is 
"not allowed".

In fairness to the GPs and their College there are "good" (i.e. not just a rule somebody made up)
reasons to avoid e-mail.

1. E-mail doesn't integrate with GP clinical software, the 3 vendors invest a lot of effort in this and, fairly, make this a big part of their
   "pitch". Other sectors either don't have an electronic records system to integrate, or (in the case of big hospitals)
   use complex systems brought in from the US where integration with Australian messaging apparently isn't possible.
   Sadly many hospitals seem happy with staff manually cut-and-pasting message texts
   between Outlook and their medical record software.

2. All but the biggest GP practices can't feasibly run their own mailserver. The result is
   e-mail for many GPs is "consumer-grade": either the e-mail account that comes with their ISP, or
   Gmail/Hotmail, and that in turn exposes them to all the security risks above.

3. E-mail traditionally was "store-and-forward": e-mails went to a server and waited
   for the recipient to log in (via dial-up modem) 
   and retrieve the message. This could be hours or days, and the sender had no idea when, or if, this happened.
   The vendors offered faster delivery and
   confirmation. Nowadays this is less of an issue, most mail clients will update
   "live" with new messages, and provide delivery confirmation ("read receipts").

The point I'm labouring here is there is a concrete, if not entirely correct, reason why the different sectors
have taken different views on the technology: big organisations can partially secure
e-mail in ways smaller operators like GPs and private specialists cannot easily do.

The Division: Private Specialists
---------------------------------

For completeness I'll mention my own 'tribe',
 but we are bit players and don't contribute much as a group.
 Essentially we are the "bad boys" of the sector: most private specialists are still on paper records
and have very little interest in the whole issue so long as the referrals keeping coming.

Many specialists are unaware of security as an issue and can't see what the problem
is with standard e-mail. This isn't just a generational thing: if
you are "young" like me, then you have been using hospital-provided e-mail
all through your registrar years without issue, so if anything we would be harder
to "re-educate" than our seniors.

Vendors to the Rescue?
----------------------

Having the health sector switch to option 4., the vendors, has been pushed as the way forward.
It's secure, it's good for integration, and some GPs have already done the "hard yards" in getting
the messaging software installed and integrated.



### 1. The weight of history.

All three messaging vendors have operated for over a decade, with Federal Government encouragement,
and, more importantly, official restraint of their main competitor technology in one major sector (General Practice). 
Despite these
'legs up' none have moved into general use, indeed (at least in my local area) slipping
backwards into obscurity amongst GPs, and never even mentioned in specialist/hospital circles.
It's unclear what would happen now to move things along.

The Federal Government could easily force the issue by using the Medicare Agreements to
command public hospitals to use one product, and
the rest of the health sector would fall in line pretty quickly. But they could have done
that at any time in the last 10, or even 20 years, and show no sign of doing so now.

Stepping back a bit, we see that the history of computing in general is littered with incompatible
proprietary products that have been dropped in favour of open solutions, despite often having fewer features.

The best example is of the commercial "pre-Internets". These were a group
of private networks, mainly US-based, accessed by dialup modem, that could not inter-communicate with each other.
They ran for about a decade: roughly early 1980s to mid-1990s.
Examples include the original [America Online](https://en.wikipedia.org/wiki/AOL#1983.E2.80.9391:_Early_years), 
[CompuServe](https://en.wikipedia.org/wiki/CompuServe), [GEnie](https://en.wikipedia.org/wiki/GEnie), and in France 
[Minitel](https://en.wikipedia.org/wiki/Minitel). They all
faded to obscurity. or morphed into ISPs, very quickly once the Internet became available.

It's important to remember these technologies had heavy corporate/Government backing in their
day, Lots of official people gravely intoned their product was The Only Way Forward.

The only real counterexample here in the annals of IT history is Microsoft: they attained enough dominance
over word-processing that their product (Word) and its file-format became the effective
standard.  This seems to be the model for the vendors, each wants to be 
the "Microsoft of messaging" and become the standard.
HealthLink have this status in New Zealand, and critical mass has been achieved in some local areas, but
no one vendor can get this dominance in Australia. In fact, each having local-area success possibly makes it worse as
it encourages each vendor to "dig in" and insist the only solution is the whole sector use their product.

### 2. Non-healthcare players

There is a lot of clinical communication between health and non-health sectors. 
As a child psychiatrist admittedly I am at the extreme
end of this: I would exchange at least 4-5 e-mails to schoolteachers, Child Protection workers, NGO social workers, etc for every 1 to
a hospital allied-health clinician or a paediatrician, but the general point applies across many areas of healthcare.

Many of these people can't use the vendors: if you are not a healthcare organisation
then you can't have a ADMA-endorsed certificate for encryption.

But, all these non-health organisations have work e-mail: for charities the national head office will provide it,
in Victoria all teachers get an e-mail in the `vic.edu.au` domain, similarly 
`dhs.vic.gov.au` for Child Protection workers. These are "free" from the point of
view of the regional bureau/school budget, and partially "secure" in terms of identity, storage and viruses like
hospital e-mail.

The other "non-healthcare player" of course, are the patients and families. Like most GPs and private specialists
they are stuck with consumer-grade e-mail, but, by and large, they don't care about security and
are keen to use it to communicate. (There is a separate issue, beyond the scope of this
essay, around how time emailing patients would be remunerated in private practice)
As now a patient of the public sector system I have realised how valuable it is to e-mail my clinicians
(who, being salaried, are happy to respond).

### 3. Money

I'm putting this here as an "anti-reason". It tends to drive a lot of angst and discussion
because historically vendors gave their service free to GPs (as primarily 'receivers')
and charged the 
'senders' (i.e. specialists) a startup fee of around [$600](https://www.medical-objects.com.au/specialists/secure-messaging/order/), and then 
for some high users a per-message fee (but generally a few cents.)

Vendor fees are trivial
compared to the other overheads of running a practice, and cheaper than other methods. Even if vendor software
could somehow be free for everyone, I don't think they would get traction, for the other reasons.

### 4. Hospital Politics

I sound critical of the vendors, but this mess isn't their fault: the "villains"
of the piece are hospital and State Government IT departments, who have spent
the past two decades ignoring this issue with iron determination.

A particular problem in hospital culture is communication with outsiders is the responsibility of junior medical staff
(interns, RMOs), who are very low down the pecking order: IT managers don't talk
to them. If they meet with any doctors at all, it will be the head consultant who
in turn has no more care for the problem than he does in his private rooms,
"that's the intern's job".

The vendors will say at this point: "the way forward is to get management on
board and rolling out our product officially, as we have in NZ/parts of Queensland/etc"
But for most of the country, 20-plus years of pestering and pleading to health managers
at all levels have got us nowhere: management just won't do it.


Proposed Solution
-----------------

> "when you have eliminated the impossible, whatever remains, however improbable, must be the truth"
Sherlock Holmes, [The Sign of the Four](http://www.gutenberg.org/etext/2097)

The first thing to point out is there is no ideal solution that offers perfect security,
interfaces seamlessly with everything, and pleases everyone: to get anywhere, trade-offs have to be made.

The core of my proposal is a specific e-mail server that is hardened so
its security is ["good enough"](http://changingminds.org/disciplines/psychoanalysis/concepts/good-enough_mother.htm),
and compatible with existing systems.

Firstly this system matches the security measures hospitals already use
(secure datacentre located in Australia, clear legal responsibility taken for server security,
e-mail addresses must reflect validated real names). Anything that could be virus (EXE or ZIP files)
would be banned.

The service would be free with registration over the web (like Gmail), paid for by private donations. Server hosting is now
so cheap this is feasible. The difference with Gmail is new users would be sent a 'welcome' letter by post
(and have to enter the confirmation key contained in the letter to keep their account active), this provides
identity security, again like hospital e-mail systems.

A big advantage it is means individual users can sign up without getting
'permission' from IT/admin (that usually just don't want to know): they can sign up and operate
using the web browser already installed.

Secondly we need to go further than the hospitals and match the
protections the vendors have with encryption: the server
will only send e-mail directly to the recipient's server, using
[STARTTLS](https://tools.ietf.org/html/rfc3207), this is an extension to the e-mail standard which
uses SSL encryption (like bank websites) for sending e-mails.

Similarly all user connections must use SSL to log in (exactly like a bank website).

In my experience of running my own mailserver (`ian@haywood.id.au`), I have found
90+% of hospital and big organisational servers already implement STARTTLS.
The 'holdouts' (who don't allow it
and force an unencrypted connection) are a couple of ISPs (Telstra and Internode)
providing consumer e-mail accounts
(and, as noted, some are stuck using these). That
means these people are excluded, unless they 'upgrade' to this system or another that supports
encryption. It is likely the no-encryption holdouts will decline over time: courtesy of Edward Snowden's
[revelations](https://en.wikipedia.org/wiki/Global_surveillance_disclosures_%282013%E2%80%93present%29)
the big Internet companies are applying increasing [pressure](https://www.act-on.com/blog/gmail-tls-encryption-and-deliverability-what-you-need-to-know/)
on other e-mail providers to use STARTTLS.

This server will also encrypt e-mails stored on disc, the encryption
key is the user's password: the folder is opened when they log in, and closed again when they log out.
The system administrator therefore has no ability to read stored e-mails.

The code that does this has been released as [open-source](http://github.com/ihaywood3/athen)
so anyone can verify what the server is doing internally, or even, if they so desire, run their own server.

This is not the highest possible standard of security as it is not true
[end-to-end encryption](https://en.wikipedia.org/wiki/End-to-end_encryption):
the server must decrypt the e-mail
as it is received, and then immediately encrypt it again before saving to disc: so the e-mail exists unencrypted
in server RAM for several microseconds when received and again when retrieved.

True end-to-end encryption by definition requires special software to be installed at both ends, such as [PGP](http://gnupg.org),
however historically these options have had even less success in healthcare than the vendors.

More to the point: it's not certain all the vendors are doing end-to-end encryption themselves.
Medical Objects have made an *en passant* [confirmation that they do](https://www.medical-objects.com.au/sending-without-pki/),
The MyEHR system does not (and in fairness cannot), and the other vendors don't say either way.
(again in fairness I don't expect any for-profit company lead
a public discussion of how their servers operate internally)
Sure, all these providers encrypt in transit, my point is messages may still exist unencrypted inside their server,
which means my proposal has equivalent security.

Fundamentally my proposition is this: we accept a less-than-perfect solution
(but a higher security level than the  MyEHR), in return for a significant
advance on the status quo for most communication already taking place in healthcare.


What I'm Asking For
-------------------

*Not funding*: unless it is wildly successful (10,000+ users), I'd still be ahead on
 buying specialist subscriptions from all 3 main vendors.

In the first instance it's feedback: is this model "good enough" in terms of security? Are
there changes that would make it so? Which GP organisation's blessing would help in terms of
people being confident they are "allowed" to use it?

If your answer is "Waste of time, total victory of product X is
soon inevitable", please explain what has changed in the past decade to make it so.

If there is support for this solution then the main issue is help with integration: users
who are willing to receive some test messages and confirm they will load correctly
in Medical Director/BP/etc.

### The Name

The original name for this project was ATHEN (Autonomous Transport for Health:
Encrypted Network): which is NEHTA backwards. NEHTA have since changed their
name to the Australian Digital Health Agency (ADHA), so finally, suggestions
for a new name would be much appreciated!
