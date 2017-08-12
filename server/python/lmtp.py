import smtplib, socket, pdb

class SMTP(smtplib.SMTP):
    """A simple class to support SMTP over UNIX sockets"""
    
    def _get_socket(self, host, port, timeout):
        "if port=-1, then host is actually a UNIX socket path"
        if port == -1:
            # use UNIX socket type
            sock = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            if timeout != socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(float(timeout))
            sock.connect(host)
            return sock
        else:
            # just use the ancestor for TCP/IP
            smtplib._get_socket(self, host, port, timeout)

