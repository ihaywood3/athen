"""mini-module for submitting new orgs/users to the Hub, in the background
runs as either cron job or as background thread from the WSGI server
"""

import pickle, os, threading

# we use Requests third-party package "pip install requests"
import requests


if __name__ == '__main__':
    import sys
    sys.path.append('../../lib')

import config
import util

def store_dict(d):
    if os.access(config.upload_file,os.R_OK):
        with open(config.upload_file,"r") as f:
            l = pickle.load(f)
    else:
        l = []
    l.append(d)
    with open(config.upload_file,"w") as f:
        pickle.dump(l,f)

def get_store():
    with open(config.upload_file,"r") as f:
        return pickle.load(f)

def clear_store():
    os.unlink(config.upload_file)

def upload_internal(data):
    res = requests.post(config.athen_api_url,cert=config.certs,verify=False,data=data) # FIXME: need to verify remote cert
    res.raise_for_status()

def upload_thread(data,logger):
    try:
        upload_internal(data)
    except:
        logger.exception("in upload_thread")
        store_dict(data) # as thread, save but silently ignore problems

def upload(data,mode,typ,logger):
    data = data.copy()
    data["mode"] = mode
    data["type"] = typ
    #upload_thread(data,logger)
    t = threading.Thread(target=upload_thread,args=(data,logger))
    t.start()
    return t

def run_main():
    for data in get_store():
        upload_internal(data)
    clear_store()   



def run_unit_tests():
    import logging
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger()
    # new organisation: should fail with same name
    t = upload({'o':'Test Organisation','street':'1 Foo St','st':'Victoria','l':'Mornington','postalCode':'3111','mail':'test@athen.email','businessCategory':'General Practice'},'new','org',logger)
    t.join()
    # create new org different name: should work
    t = upload({'o':'Test Organisation 2','street':'1 Foo St','st':'Victoria','l':'Mornington','postalCode':'3111','mail':'test@athen.email','businessCategory':'General Practice'},'new','org',logger)
    t.join()
    # create new org: invalid data
    t = upload({'o':'Test Organisation 3','street':'1 Foo St','st':'Victoria','l':'Mornington','postalCode':'31AB','mail':'test@athen.email','businessCategory':'General Practice'},'new','org',logger)
    t.join()
    # Edit existing organisation
    t = upload({'o':'Test Organisation 2','street':'2 Foo St'},'edit','org',logger)
    t.join()
    
if __name__ == '__main__':
    # we are running from cron
    # so unlike upload_thread, all errors get barfed to stderr: what we want
    #run_main()
    run_unit_tests()
