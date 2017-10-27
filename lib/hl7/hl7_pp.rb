#!/usr/bin/env ruby
$: << "/home/ian/athen/lib"
require 'hl7/message'
pp HL7::Message.parse(STDIN.read)
