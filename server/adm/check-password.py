#!/usr/bin/python
import os, sys
sys.path.extend(['../../lib','../python'])
import store
store.init_db()
u = store.User(os.environ["PAM_USER"])
if u.login(os.environ["PAM_AUTHTOK"]):
    sys.exit(0)
else:
    sys.exit(1)

