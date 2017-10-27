import smtplib, netrc, sys, email, time

_netrc = netrc.netrc()

loc = smtplib.SMTP("localhost",587)
loc.starttls()
login, _, passw = _netrc.authenticators("localhost")
loc.login(login,passw)

with open(sys.argv[1],"rb") as fd:
    msg = email.message_from_binary_file(fd)

loc.send_message(msg)
loc.quit()

time.sleep(2)

far = smtplib.SMTP("haywood.id.au",587)

far.starttls()
login, _, passw = _netrc.authenticators("haywood.id.au")
far.login(login,passw)

with open(sys.argv[2],"rb") as fd:
    msg = email.message_from_binary_file(fd)

far.send_message(msg)
far.quit()




