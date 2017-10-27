# -*- coding: utf-8 -*-
"""
OnionShare | https://onionshare.org/

Copyright (C) 2017 Micah Lee <micah@micahflee.com>

Adapted by Ian Haywood for ATHEN client

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from stem.control import Controller, Listener
from stem import ProtocolError, SocketClosed
from stem.connection import MissingPassword, UnreadableCookieFile, AuthenticationFailure
import socks
import os, sys, tempfile, shutil, urllib, platform, subprocess, time, shlex, select, socket

from . import ommon

PORT = 49042

class TorErrorAutomatic(Exception):
    """
    OnionShare is failing to connect and authenticate to the Tor controller,
    using automatic settings that should work with Tor Browser.
    """
    pass

class TorErrorInvalidSetting(Exception):
    """
    This exception is raised if the settings just don't make sense.
    """
    pass

class TorErrorSocketPort(Exception):
    """
    OnionShare can't connect to the Tor controller using the supplied address and port.
    """
    pass

class TorErrorSocketFile(Exception):
    """
    OnionShare can't connect to the Tor controller using the supplied socket file.
    """
    pass

class TorErrorMissingPassword(Exception):
    """
    OnionShare connected to the Tor controller, but it requires a password.
    """
    pass

class TorErrorUnreadableCookieFile(Exception):
    """
    OnionShare connected to the Tor controller, but your user does not have permission
    to access the cookie file.
    """
    pass

class TorErrorAuthError(Exception):
    """
    OnionShare connected to the address and port, but can't authenticate. It's possible
    that a Tor controller isn't listening on this port.
    """
    pass

class TorErrorProtocolError(Exception):
    """
    This exception is raised if onionshare connects to the Tor controller, but it
    isn't acting like a Tor controller (such as in Whonix).
    """
    pass

class TorTooOld(Exception):
    """
    This exception is raised if onionshare needs to use a feature of Tor or stem
    (like stealth ephemeral onion services) but the version you have installed
    is too old.
    """
    pass

class BundledTorNotSupported(Exception):
    """
    This exception is raised if onionshare is set to use the bundled Tor binary,
    but it's not supported on that platform, or in dev mode.
    """

class BundledTorTimeout(Exception):
    """
    This exception is raised if onionshare is set to use the bundled Tor binary,
    but Tor doesn't finish connecting promptly.
    """

class BundledTorCanceled(Exception):
    """
    This exception is raised if onionshare is set to use the bundled Tor binary,
    and the user cancels connecting to Tor
    """

class BundledTorBroken(Exception):
    """
    This exception is raised if onionshare is set to use the bundled Tor binary,
    but the process seems to fail to run.
    """


class TorIOError(Exception):
    ""Some other IO error occurred"""

class Onion(object):
    """
    Onion is an abstraction layer for connecting to the Tor control port and
    creating onion services. OnionShare supports creating onion services by
    connecting to the Tor controller and using ADD_ONION, DEL_ONION.

    stealth: Should the onion service be stealth?

    settings: A Settings object. If it's not passed in, load from disk.

    bundled_connection_func: If the tor connection type is bundled, optionally
    call this function and pass in a status string while connecting to tor. This
    is necessary for status updates to reach the GUI.
    """
    def __init__(self, tor_status_update_func=None):
        common.log('Onion', '__init__')

        self.stealth = False
        self.service_id = None

        self.system = platform.system()

        # Is bundled tor supported?
        if (self.system == 'Windows' or self.system == 'Darwin'):
            self.use_bundle = True

        # Set the path of the tor binary, for bundled tor
        (self.tor_path, self.tor_geo_ip_file_path, self.tor_geo_ipv6_file_path) = common.get_tor_paths()

        # The tor process
        self.tor_proc = None

        # Start out not connected to Tor
        self.connected_to_tor = False

        common.log('Onion', 'start')

        # Load settings from disc/registry if we can
        self.settings = common.get_settings()

        # The Tor controller
        self.c = None

        if self.use_bundle and not self.settings.get('suppress_bundle',False):

            # Create a torrc for this session
            self.tor_data_directory = tempfile.TemporaryDirectory()

            if self.system == 'Windows':
                # Windows needs to use network ports, doesn't support unix sockets
                torrc_template = open(common.get_resource_path('torrc_template-windows')).read()
                self.tor_control_port = common.get_available_port(1000, 65535)
                self.tor_control_socket = None
                self.tor_cookie_auth_file = os.path.join(self.tor_data_directory.name, 'cookie')
                self.tor_socks_port = common.get_available_port(1000, 65535)
                self.tor_torrc = os.path.join(self.tor_data_directory.name, 'torrc')
            else:
                # Linux and Mac can use unix sockets
                with open(common.get_resource_path('torrc_template')) as f:
                    torrc_template = f.read()
                self.tor_control_port = None
                self.tor_control_socket = os.path.join(self.tor_data_directory.name, 'control_socket')
                self.tor_cookie_auth_file = os.path.join(self.tor_data_directory.name, 'cookie')
                self.tor_socks_port = common.get_available_port(1000, 65535)
                self.tor_torrc = os.path.join(self.tor_data_directory.name, 'torrc')

            torrc_template = torrc_template.replace('{{data_directory}}',   self.tor_data_directory.name)
            torrc_template = torrc_template.replace('{{control_port}}',     str(self.tor_control_port))
            torrc_template = torrc_template.replace('{{control_socket}}',   str(self.tor_control_socket))
            torrc_template = torrc_template.replace('{{cookie_auth_file}}', self.tor_cookie_auth_file)
            torrc_template = torrc_template.replace('{{geo_ip_file}}',      self.tor_geo_ip_file_path)
            torrc_template = torrc_template.replace('{{geo_ipv6_file}}',    self.tor_geo_ipv6_file_path)
            torrc_template = torrc_template.replace('{{socks_port}}',       str(self.tor_socks_port))
            with open(self.tor_torrc, 'w') as f:
                f.write(torrc_template)

            # Execute a tor subprocess
            start_ts = time.time()
            if self.system == 'Windows':
                # In Windows, hide console window when opening tor.exe subprocess
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                self.tor_proc = subprocess.Popen([self.tor_path, '-f', self.tor_torrc], startupinfo=startupinfo)
            else:
                self.tor_proc = subprocess.Popen([self.tor_path, '-f', self.tor_torrc])

            # Wait for the tor controller to start
            time.sleep(2)

            # Connect to the controller
            try:
                if self.system == 'Windows':
                    self.c = Controller.from_port(port=self.tor_control_port)
                    self.c.authenticate()
                else:
                    self.c = Controller.from_socket_file(path=self.tor_control_socket)
                    self.c.authenticate()
            except Exception as e:
                raise BundledTorBroken('settings_error_bundled_tor_broken: {}'.format(e.args[0]))

            while True:
                try:
                    res = self.c.get_info("status/bootstrap-phase")
                except SocketClosed:
                    raise BundledTorCanceled()

                res_parts = shlex.split(res)
                progress = res_parts[2].split('=')[1]
                summary = res_parts[4].split('=')[1]

                # "\033[K" clears the rest of the line
                print("{}: {}% - {}{}".format('connecting_to_tor', progress, summary, "\033[K"), end="\r")

                if callable(tor_status_update_func):
                    if not tor_status_update_func(progress, summary):
                        # If the dialog was canceled, stop connecting to Tor
                        common.log('Onion', 'connect', 'tor_status_update_func returned false, canceling connecting to Tor')
                        print()
                        return False

                if summary == 'Done':
                    print("")
                    break
                time.sleep(0.2)

                # Timeout after 45 seconds
                if time.time() - start_ts > 45:
                    print("")
                    self.tor_proc.terminate()
                    raise BundledTorTimeout(strings._('settings_error_bundled_tor_timeout'))

        else:
            # Automatically try to guess the right way to connect to Tor Browser

            # Try connecting to control port
            found_tor = False

            # If the TOR_CONTROL_PORT environment variable is set, use that
            env_port = os.environ.get('TOR_CONTROL_PORT')
            if env_port:
                try:
                    self.c = Controller.from_port(port=int(env_port))
                    found_tor = True
                except:
                    pass

            else:
                # Otherwise, try default ports for Tor Browser, Tor Messenger, and system tor
                try:
                    ports = [9151, 9153, 9051]
                    for port in ports:
                        self.c = Controller.from_port(port=port)
                        found_tor = True
                except:
                    pass

                # If this still didn't work, try guessing the default socket file path
                if not found_tor:
                    try:
                        try_sockets = []
                        if 'socket_path' in self.settings:
                            try_sockets.append(self.settings['socket_path'])
                        if 'TOR_CONTROL_SOCKET' in os.environ:
                            try_sockets.append(os.environ['TOR_CONTROL_SOCKET'])
                        if self.system == 'Darwin':
                            try_sockets.extend([os.path.expanduser('~/Library/Application Support/TorBrowser-Data/Tor/control.socket'),'/run/user/{}/Tor/control.socket'.format(os.geteuid())])
                        elif self.system == 'Linux':
                            try_sockets.extend(['/var/run/tor/control','/run/user/{}/Tor/control.socket'.format(os.geteuid())])
                        for i in try_sockets:
                            self.c = Controller.from_socket_file(path=socket_file_path)
                            found_tor = True
                            break
                    except:
                        pass
            self.tor_socks_port = 9050 # assume standard port


            if not found_tor:
                raise TorErrorAutomatic('settings_error_automatic')

            # Try authenticating
            try:
                self.c.authenticate()
            except MissingPassword:
                raise TorErrorMissingPassword('settings_error_missing_password')
            except UnreadableCookieFile:
                raise TorErrorUnreadableCookieFile('settings_error_unreadable_cookie_file')
            except AuthenticationFailure:
                raise TorErrorAuthError('settings_error_auth')
            #except:
            #    raise TorErrorAutomatic('settings_error_automatic')

        # If we made it this far, we should be connected to Tor
        self.connected_to_tor = True

        # Get the tor version
        self.tor_version = self.c.get_version().version_str

        # Do the versions of stem and tor that I'm using support ephemeral onion services?
        list_ephemeral_hidden_services = getattr(self.c, "list_ephemeral_hidden_services", None)
        supports_ephemeral = callable(list_ephemeral_hidden_services) and self.tor_version >= '0.2.7.1'
        if not supports_ephemeral:
            raise TorTooOld('error ephermeral not supported')

    def start_onion_service(self):
        """
        Start a onion service, pointing to the given port, and
        return the onion hostname.
        """
        common.log('Onion', 'start_onion_service')
        port = common.get_available_port(40000,65535)
        try:
            hidden_service_dir = os.path.join(controller.get_conf('DataDirectory',common.get_data_directory()), 'athen')
            print(" * Creating our hidden service in %s" % hidden_service_dir)
            result = controller.create_hidden_service(hidden_service_dir, PORT, target_port = port)
            # The hostname is only available when we can read the hidden service
            # directory. This requires us to be running with the same user as tor.
            
            if result.hostname:
                print(" * Our service is available at %s" % result.hostname)
            else:
                raise TorErrorAuthError("cannot read hidden data dir {}".format(hidden_service_dir))
        except ProtocolError:
            raise TorErrorProtocolError('error_tor_protocol_error')
        return (result.hostname,port)

    def cleanup(self):
        """
        Stop onion services that were created earlier. If there's a tor subprocess running, kill it.
        """
        common.log('Onion', 'cleanup')
        # Stop tor process
        if self.tor_proc:
            self.tor_proc.terminate()
            time.sleep(0.2)
            if not self.tor_proc.poll():
                self.tor_proc.kill()
            self.tor_proc = None

        # Reset other Onion settings
        self.connected_to_tor = False
        self.service_id = None

    def get_tor_socks_port(self):
        """
        Returns a (address, port) tuple for the Tor SOCKS port
        """
        common.log('Onion', 'get_tor_socks_port')
        try: 
            listeners = self.c.get_listeners(Listener.SOCKS)
            return listeners[0]
        except:
            return ('127.0.0.1',self.tor_socks_port)

    def connect(self, addr, port):
        """
        make a connection out using SOCKS
        """
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, *self.get_socks_port())
        s.connect((addr,port))
        return s

    def listen(self):
        """Start listening for incoming connections
        """
        self.sock = socket.socket()
        self.hostname, port = self.start_onion_service()
        self.sock.bind(('127.0.0.1',port))
        self.sock.listen()
        
    def accept(self, timeout=30.0):
        """Wait timeout sec for a connection
        Returns connected socket or None"""
        rfs, wfds, efds  = select.select([self.sock],[],[self.sock],timeout)
        if efds:
            raise TorIOError("listening socket in error")
        if rfds:
            newsock, _ = self.sock.accept()
            return newsock
        return None
    
        
