#!/usr/bin/ruby

$: << File.join(File.expand_path(File.dirname(__FILE__)),"..","lib")
require 'rubygems'
require 'file'
require 'mail'
require 'getoptlong'
require 'interfaces'

# main code

GetoptLong.new(
  ['--help','-h',GetoptLong::NO_ARGUMENT],
  ['--version','-v',GetoptLong::NO_ARGUMENT],
  ['--licence',GetoptLong::NO_ARGUMENT],
  ['--conffile','-c',GetoptLong::REQUIRED_ARGUMENT],
  ['--logfile','-l',GetoptLong::REQUIRED_ARGUMENT]).each do |opt,arg|
    case opt
      when "--version":
        print "ATHEN 0.1\n"
        exit
      when "--licence"
        print <<EOF
    ATHEN -  a program to send/recieve HL7 via OpenPGP/SMTP
    Copyright (C) 2008,2010 Ian Haywood

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
EOF
        exit
      when "--help":
        print <<EOF
ATHEN options and commands
Options:
   --help - this message
   --version, -v - version information
   --licence -  licence information
   --conffile, -c file - set configuration file
   --logfile, -l - set logging file

Commands:
  pop - fetch e-mails via POP3
  imap - fetch e-mails via IMAP (note tries to runs forever using the IDLE command)
  mail - receive mail on standard input
  scan - scan input directory and send
  resend - resend unACKnowledged messages
  trust - resend messages waiting for new trusted keys

Note more than one command can be run at once
EOF
    when "--conffile":
      Athen.set_config(arg)
    when "--logfile"
      $cfg['logfile'] = arg
  end
end
  
is_setup = false
iface = Athen::CliInterface.new
ARGV.each do |cmd|
  unless is_setup
    Athen.setup
    is_setup = true
  end
  case cmd
    when 'pop': Athen.receive_mails_pop
    when 'imap': Athen.receive_mails_imap
    when 'mail': Athen.pgp_decrypt(STDIN.read)
    when 'scan': Athen.scan_files
    when 'resend': Athen.resend
    when 'trust': Athen.resend_trust 
  end
end

$logfile.close if is_setup
