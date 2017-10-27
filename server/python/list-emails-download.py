#!/usr/bin/env python3
# list email files for download
# called via ssh by downloader clients
# assumes ssh has set the process uid correctly
# and set the common environment variables already

# errors: short line should be dumped to stderr and non-zero exit status

DOWNLOADABLE_MIME_TYPES = ['text/x-pit','applicaton/edi-hl7']

import deliver

import util, config, userdb

import os, os.path, email, logging, sys

try:
    global uctx
    uctx = deliver.get_user_context() # using $USER set by ssh
    emaildir = os.path.join(uctx["HOME"],"mail")
    if not os.access(emaildir,os.X_OK):
        # we are not logged in
        raise util.AthenError("directory {} not available".format(emaildir))
    # now scan all mails in maildir INBOX
    # FIXME: use Download mailbox and if so when?
    all_attachment_fnames = set()
    udb = userdb.UserDB()
    for subdir in ["cur","new"]:
        for fname in os.listdir(os.path.join(emaildir,subdir)):
            fpath = os.path.join(emaildir,subdir,fname)
            try:
                with open(fpath,"rb") as fd:
                    msg = email.message_from_binary_file(fd)
                if not 'Message-Id' in msg:
                    logging.warn("%r has no Message-Id" % fname)
                else:
                    for part in msg.walk():
                        if part.get_content_type() in DOWNLOADABLE_MIME_TYPES:
                            atlachment_fname = part.get_filename()    
                            if not attachment_fname is None:
                                ext = attachment_fname.split('.')[-1][:3].upper()
                                if attachment_fname in all_attachment_fnames:
                                    attachment_fname = None # don't use duplicate names in this run FIXME: should we check further back in time?
                            else:
                                ext = None
                            if attachment_fname is None:
                                # synthesise a name from the udb
                                run_no, initial = udb.get_run_from_sender(msg['From'])
                                if ext is None:
                                    if part.get_content_type() == 'text/x-pit':
                                        ext = 'PIT'
                                    elif part.get_content_type() == 'application/edi-hl7':
                                        ext = 'ORU'
                                    else: # shouldn't happen but may need to expand for different MIME types
                                        logging.warn("I don't know the extension for MIME %r" % part.get-content_type())
                                        ext = 'DAT'
                                attachment_fname = '{}{:0>5}.{}'.format(initial, run_no % 100000, ext)
                            all_attachment_names.add(attachment_fname)
                            with open(os.path.join(uctx['HOME'],'download',attachment_fname),'wb') as fd:
                                fd.write(part.get_payload(decode=True))
                            sys.stdout("%s\t%s\n" % msg['Message-Id'],attachment_fname)
            except FileNotFoundError:
                logging.warn("%r vanished (? moved by Dovecot)" % fpath)
                # but don't otherwise complain about missing files
            except:
                logging.panic("exception during extraction of %r" % fpath)
                raise
except:
    logging.exception("in list-email-download")
                                        
                                

