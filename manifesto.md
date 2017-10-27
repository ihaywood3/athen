
Clinical Messaging in Australia
================================

Taking the 10,000ft view, there are four ways
health practitioners and organisations can send messages to each other in Australia.

1. Paper letters.
2. Fax. Fax transmission is an official 'open' [standard](http://www.itu.int/rec/T-REC-T.30/en)
By "open standard" I mean that a fax machine made by, say, Canon, can send and receive faxes from one made by
Hewlett-Packard, and not because Canon got 'permission' from HP to do this.
3. Email, by this I mean transmissions based on the [SMTP standard](https://tools.ietf.org/html/rfc821) and its
various extensions. Again it is "open": any standard-compliant mailserver
can intercommunicate with any other.
4. Several commercial messaging products. This began with the pathology companies who provided (and still do) their own programs
such as Fetch to allow GPs to download reports. Now the 3 most common for general messaging are Argus (now "Telstra Health"), 
[Medical-Objects](https://www.medical-objects.com.au/), and [HealthLink](http://www.healthlink.net). Hereafter
I refer to them as ``the vendors''. 

    Crucially, unlike the other 3 technologies, the vendors cannot easily interoperate with
    each other: Argus users cannot message Medical-Objects users, etc.
	[Encouragement](https://www.digitalhealth.gov.au/get-started-with-digital-health/what-is-digital-health/secure-messaging)
	from the regulator
    (the "Australian Digital Health Agency") to use a standard has not changed this problem. Exactly why this happens is an essay in itself(and not one I wish to write!)
    Suffice it to say here, interoperability
    is hard for reasons largely outside of the vendors' control, and won't be 'fixed' soon
    <sup>[1](#fn1</sup>.

All four methods are in widespread use and there is general agreement this
isn't an ideal state of affairs. Nevertheless things have been remarkably static
over the last 10--15 years, despite massive changes in how the rest of the country
communicates, the health sector seems wedged uncomfortably between the old and the new.

However, this arrangment can't last, post and fax are on an inevitable decline
forcing a choice between 3. and 4, which is where the core issues arises: as a sector
we can't decide. GPs rarely use e-mail
on the grounds of security, but, rightly or wrongly, all other health sectors are using it increasingly.

Consequently communication with GPs is mainly
by fax, being still the highest technology in common.
This could be potentially bad for general practice as the NBN means loss of fax lines
<sup>[2]{#fn2)</sup>.
GPs risk being "punished for
doing the right thing": isolated from the rest of the health system because they
won't compromise on messaging security.


Message Security
----------------

The security problems of any messaging system fit into 4 categories. Systems are
not "secure" or "insecure" as a binary property, but exist on a continuum in terms of how they address them.

1.  Identity security: the ability to know the message is going to
the right person. We trust posties give the letter to the address
written on the letter, for example.

2.  Storage security, the lock on the mailbox. Fax machines don't have a lock, but are seen as safe-ish because the fax machine
is usually located inside recipient's office: a printed fax sitting on the tray is no more or less secure than all the other bits
of paper lying around.

3.  Payload security: people sending you "bad stuff" like advertising, scams and viruses.

4.  Transport security, the envelope. For faxes we assume (rightly or wrongly) the phone line is 'secure'. Encryption provides transport security for electronic communications.

The Division: Hospitals
-----------------------

The main change I have seen in the last 2--3 years is local
<sup>[3]{#fn3)</sup> public hospitals have 'blinked' and started
e-mailing, unencrypted, clinical documents in a range of contexts. They are not doing it automatically: if I wanted a discharge summary, for example, I or my secretary had to ask
a human (usually an allied health clinician in the target department) to manually email it to me, but it is happening.

Medicare have also 'blinked' on the issue:
by 2015 I started receiving specialist-to-specialist referrals from the younger colleagues via e-mail, and this
was acceptable for Medicare billing at the consultant rate.

Lots of other organisations in and around health have been routinely using e-mail for some time: schools, NGO charities,
Child Protection (known as "DOCS" north of the Murray), police, allied
health, psychologists, etc, etc <sup>[4](#fn4)</sup>

I suspect the main reason is for this shift is hospitals and other large organisations have for some time run 
(or commissioned an IT firm to run for them) their own e-mail servers. This has allowed them to manage *some*
of the security issues above:

1.  They can make the e-mail address reflect the legal name of the individual and their employer. For example
    as a registrar at Austin Hospital my e-mail was `Ian.Haywood@austin.org.au`. This fixes the identity
    security problem (at their end anyway),
    and;

2.  Brings storage security under their control: like the fax machine it's now "inside the office"

3.  With control of the server organisations, have gained confidence in mitigating 
    payload attacks such as viruses and "phishing": using hospital e-mail for many years I found spam and viruses
    were quite rare.

None of this addresses the transmission security issue, of course: e-mails can still leave and enter
the hospital network unencrypted. 


The Division: GPs
-----------------

The main proximate reason GPs don't e-mail clinical documents is they are "not allowed": GPs remain under [formal advice](http://www.racgp.org.au/your-practice/ehealth/protecting-information/email/) 
e-mail is not secure
enough. Many GPs assume this is "the law" and binding across the entire sector, but this contradicts the experience of myself and many others.

It's worth reminding GP readers that the rest of the health sector doesn't have accreditation
as they understand it: we [private specialists] have resisted the concept, and hospital accreditation works exclusively with admin around management processes: 
there's no fellow with a clipboard walking the wards and quizzing interns how 
they securely communicate with GPs. So there is no-one to tell the other sectors of the health system e-mail is 
"not allowed".

In fairness to the GPs and their College there have been "good" (i.e. not just a rule somebody made up)
reasons to avoid e-mail.

1. E-mail doesn't integrate with GP clinical software, the vendors invest a lot of effort in this. (and arguably
that's the main service they offer, not actual message transport)
   Other sectors either don't have an electronic records system to integrate, or (in the case of big hospitals)
   integration with messaging is a low priority for the
   hospital and the systems vendor. Even when they do support messaging, it often imposes a very limited workflow:
   usually the intern can only send one discharge summary using a bulky fixed template at the end of the admission, they
   can't send messages at other times, nor receive messages from outside at all.
   Sadly many hospitals seem happy with what I did as a registrar:  manually cut-and-pasting messages
   between Microsoft Outlook and their medical record software.

2. All but the biggest practices can't feasibly run their own mailserver. The result is
   e-mail for many GPs and private specialists  is "consumer-grade": either the e-mail account that comes with their ISP, or
   Gmail/Hotmail, and that in turn exposes them to all four security risks above.

3. E-mail traditionally was "store-and-forward": e-mails went to a server and waited
   for the recipient to intermittently log in (via dial-up modem) 
   and retrieve the message. This could be hours or days, and the sender had no idea when, or if, this happened.

The point I'm labouring here is there is a concrete reason why the different sectors
have taken different views on the technology: big organisations can partially secure
e-mail in ways smaller operators like GPs and private specialists cannot easily do.

The Division: Private Specialists
---------------------------------

For completeness I'll mention my own 'tribe',
 but we are bit players.
 Essentially we are the "bad boys" of the sector: most private specialists are still on paper records
and have very little interest in the whole issue. Again remember there's no ePIP or other requirement/incentive for us to use IT at all.

Most specialists are unaware of security as an issue and can't see what the problem
is with standard e-mail. This isn't just a generational thing: if
you are "young" like me, then you have been using hospital-provided e-mail
all through your training years without issue, so it's going to be
tough sell to convince us that we are suddenly "not allowed" to use e-mail upon
attaining Fellowship.

The Vendor Solution
----------------------

Traditionally most players have expected the health sector to move eventually to option 4., the vendors, over time.
It's secure, it's integrated, and many GPs have done the hard yards in getting
 multiple messaging software packages installed on their computers and integrated with their record systems.

Although it's the best solution in many ways, it's going to be a long wait.

### 1. History.

All three messaging vendors have operated for over a decade, Argus for nearly 20 years,
None have moved into general use, indeed (at least in my local area) slipping
backwards into obscurity amongst GPs, and never mentioned in specialist/hospital circles.
Sadly, it's unclear what would or could happen now to move things along.

The Federal Government could easily force the issue by using the Medicare Agreements to
command public hospitals to use one product, and
the rest of the health sector would fall in line pretty quickly. But they could have done
that at any time in the last 20 years, and show no more sign of doing so now than at any previous time.

Stepping back a bit, we see that the history of computing in general is littered with incompatible
proprietary products that have been dropped in favour of open solutions, despite often having fewer features.

The best example is of the commercial "pre-Internets". These were a group
of private networks, mainly US-based, accessed by dialup modem, that could not inter-communicate with each other.
They ran for about a decade: roughly early 1980s to early 90s.
Examples include the original [America Online](https://en.wikipedia.org/wiki/AOL#1983.E2.80.9391:_Early_years), 
[CompuServe](https://en.wikipedia.org/wiki/CompuServe), [GEnie](https://en.wikipedia.org/wiki/GEnie), and in France 
[Minitel](https://en.wikipedia.org/wiki/Minitel). They all
faded to obscurity. or morphed into ISPs, very quickly once the Internet became available.

It's important to remember these technologies had heavy corporate/Government backing in their
day, Lots of official people gravely intoned product X was The Way Forward.

The main counterexample here in the annals of IT history is Microsoft: they attained enough dominance
over word-processing that their product (Word) and its file-format became the effective
standard.  A private vendor model could only work if one becomes the "Microsoft of messaging" and gets to set the standard.
HealthLink have this status in New Zealand, but no one vendor can get this dominance in Australia. 

### 2. Non-healthcare players

There is a lot of clinical communication between health and non-health sectors. 
As a child psychiatrist admittedly I am at the extreme
end of this: I would exchange at least 4-5 e-mails to Family Court lawyers, schoolteachers, Child Protection workers, NGO social workers, etc for every 1 to
a hospital allied-health clinician or a paediatrician, but the general point applies across many areas of healthcare.

Many of these people can't (easily) use the vendors: if you are not a healthcare organisation
then you can't have a ADMA-endorsed certificate for encryption. [For completeness, 
at least Medical-Objects do support using non-ADMA certificates, so presumably they would licence a school or a NGO social worker if they requested it]

But, all these non-health organisations have work e-mail: for charities the national head office will provide it,
in Victoria all teachers get an e-mail in the `vic.edu.au` domain, similarly 
`dhs.vic.gov.au` for Child Protection workers. These are "free" from the point of
view of the regional bureau/school budget, and partially "secure" in terms of identity, storage and viruses like
hospital e-mail.

The other "non-healthcare player" of course, are the patients and families. Like most GPs and private specialists
they are stuck with consumer-grade e-mail, but, by and large, they don't care and
are keen to use it to communicate. (There is a separate issue, beyond the scope of this
essay, around how time emailing patients would be remunerated in private practice)
As now a patient of the public sector system I have realised how valuable it is to e-mail my clinicians
(who, being salaried, are happy to respond).

### 3. Money

I'm putting this here as an "anti-reason". It tends to drive a lot of angst and discussion
because historically some vendors gave their service free to GPs (being primarily 'receivers')
and charged the 
'senders' (i.e. specialists) a startup fee of around [$600](https://www.medical-objects.com.au/specialists/secure-messaging/order/), and then 
for some high users a per-message fee (but generally a few cents.)

Vendor fees are trivial
compared to the other overheads of running a practice, and cheaper than other methods. Even if vendor software
could somehow be free for everyone, I don't think they would get traction, for the other reasons.

### 4. Hospital Politics

I may sound critical of the vendors, but this isn't their fault: the "villains"
of this drama are hospitals and Government health departments, who have spent
the past two decades either ignoring or mismanaging this issue with fanatical determination.

A particular problem in hospital culture is communication with outsiders is the responsibility of junior medical staff
(interns, RMOs), who are very low down the pecking order: managers don't talk
to them. If they meet with any doctors at all, it will be the unit head consultant who
in turn has no more care for the problem than he/she does in his/her private rooms,
"that's the intern's job".

The vendors and others will say at this point: "the way forward is to get management on
board and rolling out our product officially, as we have in NZ/parts of Queensland/etc"
But for most of the country, 20-plus years of pestering and pleading to health managers
at all levels have got us nowhere: "management" just aren't interested.


Proposed Solution
-----------------

> "when you have eliminated the impossible, whatever remains, however improbable, must be the truth"
Sherlock Holmes, [The Sign of the Four](http://www.gutenberg.org/etext/2097)

The first thing to point out is there is no ideal solution that offers perfect security,
interfaces seamlessly with everything, and pleases everyone: to get anywhere, trade-offs have to be made.

The core of my proposal is a specific e-mail server that is hardened so
its security is ["good enough"](http://changingminds.org/disciplines/psychoanalysis/concepts/good-enough_mother.htm),
its compatible with hospital/NGO e-mail, and on the other side tries to play nice with GP
medical records systems.

Firstly this system matches the security measures hospitals already use
(secure datacentre located in Australia, clear legal responsibility taken for server security,
e-mail addresses must reflect validated real names). Anything that could be virus (EXE or ZIP files)
would be banned.

The service would be free with registration over the web (like Gmail), paid for by private donations. Server hosting is now
so cheap this is feasible. The difference with Gmail is new users would be sent a 'welcome' letter by post
(and have to enter the confirmation key contained in the letter to keep their account active), this provides
identity security, again like hospital e-mail systems.

A big advantage it is means individual users in hospitals can sign up without getting
'permission' from the IT department/ central admin (that generally just don't want to know): they can sign up and operate
using the web browser already installed on the terminals at work or a smartphone.

Secondly we need to go further than the hospitals and use encryption: the server
will only send e-mail directly to the recipient's server, using
[STARTTLS](https://tools.ietf.org/html/rfc3207), this is an extension to the e-mail standard which
uses SSL encryption (like bank websites) for sending e-mails.

Similarly all user connections must use SSL encryption to log in (so exactly like a bank website).

In my experience of running my own mailserver (`ian@haywood.id.au`), I have found
90+% of hospital and big organisational servers already implement STARTTLS.
The 'holdouts' (who don't support it and only allow old-style unencrypted connections) are a couple of ISPs (Telstra and Internode)
providing consumer e-mail accounts
(and, as noted, some are stuck using these). That
means these people are excluded, unless they 'upgrade' to this system or another that supports
encryption. It is likely the no-encryption holdouts will decline over time: courtesy of Edward Snowden's
[revelations](https://en.wikipedia.org/wiki/Global_surveillance_disclosures_%282013%E2%80%93present%29)
the big Internet companies are applying increasing [pressure](https://www.act-on.com/blog/gmail-tls-encryption-and-deliverability-what-you-need-to-know/)
on other e-mail providers to use STARTTLS.

This server will also encrypt e-mails stored on disc, the encryption
key is the user's password: the user folder is opened when they log in, and closed again when they log out.
The system administrator therefore has no independent ability to read stored e-mails.

The code that does this has been released as [open-source](http://github.com/ihaywood3/athen)
so anyone can verify what the server is doing internally, or even, if they have the means, run their own server.

This is not the highest possible standard of security as it is not true
[end-to-end encryption](https://en.wikipedia.org/wiki/End-to-end_encryption):
the server must decrypt the e-mail
as it is received, and then immediately encrypt it again before saving to disc: so the e-mail exists unencrypted
in server RAM for several microseconds when received and again when retrieved.

True end-to-end encryption by definition requires special software to be installed at both ends, such as [PGP](http://gnupg.org),
however historically these options have had no success in healthcare..

More to the point: it's not clear that all the 'secure' message providers are doing end-to-end encryption themselves.
Medical Objects [do](https://www.medical-objects.com.au/sending-without-pki/),
The patholgist's Fetch and the MyEHR system do not, and the other vendors don't say either way.
(in fairness I don't expect any for-profit company to lead
a public discussion of how their servers operate internally)
Sure, the MyEHR and all these providers are 'secure' because they encrypt in transit, my point is messages exist unencrypted inside their server,
which means my proposal has equivalent security.

Fundamentally my proposition is this: we accept a less-than-perfect solution
(but a equivalent security level to the MyEHR), in return for a significant
advance on the status quo for most communication already taking place in healthcare.

The server will also improve on standard e-mail by making a "best effort" attempt to translate messages into the HL7 format so they
can be imported into Medical Director/Best Practice/Zedmed etc. This won't work
100% of the time, the user will still have to check their inbox
 and decide what do to, like "ordinary" e-mail. This is the same as the in-tray of a fax machine: not every fax
is filed in a medical record, as not every fax pertains to a patient, so somebody has to go through the faxes and decide
what to do with them. In terms of total office workload however, it's at worst the same (because e-mailed messages won't be posted or faxed),
and better some of the time for messages the system can convert to HL7.

I need to hammer this point a bit: this system won't even try to match what the vendors do in terms of integration,
because this system can't control what is sent to it (and this mirrors the reasons the vendors can't link up
with each other): this is about providing a *good enough* system to shift the messages currently sent by post/fax/unencrypted e-mail.
It's not meant to replace what is currently coming through the vendor systems.

What I'm Asking For
-------------------

*Not funding*: unless it is wildly successful (10,000+ users), hosting the service is equivalent to
 buying specialist subscriptions from all the vendors.

In the first instance it's feedback: is this model "good enough" in terms of security? Are
there changes that would make it so? Which organisations' blessing would help in terms of
GPs being confident they are "allowed" to use it?

If your answer is "Waste of time, total victory of product X/standard Y is
soon inevitable", please explain what has changed in the past 20 years to make it so.

If there is support for this solution then the main issue is help with integration: users
who are willing to receive some test messages and confirm they will load correctly
in Medical Director/Best Practice/Zedmed/etc.

### The Name

The original name for this project was ATHEN (Autonomous Transport for Health:
Encrypted Network): which is NEHTA backwards. NEHTA have since changed their
name to the Australian Digital Health Agency (ADHA), so finally, suggestions
for a new name would be much appreciated!

Related Documents
-----------------

The [whitepaper](whitepaper.md) is a technical run-through of how
the system works.

A [user guide](userguide.md) will get written, promise.

Footnotes
---------

<a name="fn1">1:</a> Thanks to two of the vendors for answering my queries on this point

<a name="fn2">2:</a>Yes there are fax-to-email gateways, but that somewhat undermines the argument that e-mail isn't secure enough for healthcare

<a name="fn3">3:</a>For me that's south-eastern Melbourne. Maybe we are a messaging backwater and the rest of the country are merrily
charging ahead with product X. But if so they are being remarkably coy about it.

<a name="fn4">4:</a>This different attitude was driven home to me personally two years ago: a patient of mine died, being a ward of the State at the time of her death.
Information about the death of a ward of the Stateis extremely sensitive both politically and clinically. Nevertheless all the players (police, DOCS, even the Coroner's court staff)
were completely relaxed about sending and receiving reports from me via e-mail.
