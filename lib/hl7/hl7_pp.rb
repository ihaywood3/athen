#!/usr/bin/env ruby
$: << "~/wedgetail/lib"
require 'hl7/message'
pp HL7::Message.parse(STDIN.read)
