#!/usr/bin/ruby

require 'file'
require 'mail'
require 'getoptlong'

# main code
$cfg = {}

GetoptLong.new(
  ['--help','-h',GetoptLong::NO_ARGUMENT],
  ['--version','-v',GetoptLong::NO_ARGUMENT],
  ['--licence',GetoptLong::NO_ARGUMENT],
  ['--conffile','-c',GetoptLong::REQUIRED_ARGUMENT],
  ['--logfile','-l',GetoptLong::REQUIRED_ARGUMENT]).each do |opt,arg|
    case opt
      when "--version":
        print "wedgechick 0.1\n"
        exit
      when "--licence"
        print <<EOF
    Wedgechick -  a program to send/recieve HL7 via OpenPGP/SMTP
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
wedgechick options commands
Options:
   --help - this message
   --version, -v - version information
   --licence -  licence information
   --conffile, -c file - set configuration file
   --logfile, -l - set logging file

Commands:
  pop - fetch e-mails via POP3
  mail - receive mail on standard input
  scan - scan input directory and send
  resend - resend unACKnowledged messages
  trust - resend messages waiting for new trusted keys

Note more than one command can be run at once
EOF
    when "--conffile":
      set_config(arg)
    when "--logfile"
      $cfg['logfile'] = arg
  end
end
  
is_setup = false
ARGV.each do |cmd|
  unless is_setup
    setup
    is_setup = true
  end
  case cmd
    when 'pop': receive_mails
    when 'mail': pgp_decrypt(STDIN.read)
    when 'scan': scan_files
    when 'resend': resend
    when 'trust': resend_trust 
  end
end

$logfile.close if is_setup
