import os, sys
try:
    sys.path.append('../../lib')
    from util import *
    import config, store, submit, myldap

    u = store.User(os.environ["PAM_USER"])
    if u.login(os.environ["PAN_AUTHTOK"]):
        sys.exit(0)
    else:
        sys.exit(1)
except:
    sys.exit(1)
