#!/usr/bin/env python3

"""
Called from ssh when a file has been downloaded (or otherwise changed state)
Updated the user log appopriately
"""

# note not for end-user use, won't play nice if called wrongly.

import sys

message_id = sys.argv[1]
fname = sys.argv[2]
status = sys.argv[3]
comment = sys.argv[4]

if status == "PANIC":
    level = 3
    action="failed"
    ostatus="5.3.0"
    txt_report="There was a problem with the remote system downloading the file.\nError message:\n\n%r" % comment
    comment = comment.split("\n")[0]
    diagnostic = "remote-panic: %r" % comment
if status == "DOWNLOADED":
    level = 1
    action="relayed"
    diagnostic="remote-downloaded"
    ostaatus="2.0.0"
    txt_report="Message downloaded to remote system, awaiting pickup"
if status == 'DELETED':
    txt_report = "File deleted on remote system so we assume successfully processed by the remote EMR"
    level = 1
    action="delivered"
    ostatus="2.0.0"
    diagnostic="remote-deleted"
    
import deliver
import userdb, dsn

udb = UserDB() # $HOME set by ssh

udb.update_messages(message_id,status,fname=fname)
udb.write_log_entry(comment, "", level)

# now generate dsn for sender

msg_data = udb.get_message_by_id()

deliver.postfix_deliver(dsn.prepare_dsn_report(self,orig_msg=None,txt_report=txt_report,action=action,status=ostatus,diagnostic=diagnostic,dest=msg_data['temail'],msg_id=message_id))
