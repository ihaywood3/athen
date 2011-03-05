require 'hl7/field'
require 'hl7/types'
require 'hl7/segment'
require 'hl7/error'
require 'hl7/msa'
require 'hl7/msh'
require 'hl7/obr'
require 'hl7/obx'
require 'hl7/orc'
require 'hl7/pid'
require 'hl7/prd'
require 'hl7/pv1'
require 'hl7/rf1'
require 'pp'

module HL7
  class Message

    def initialize(segs=[])
      @segments = segs
      segs.each {|s| s.parent = self}
    end
  
    # add a segment to the end of the message
    def << (x)
      if x.kind_of? HL7::Segment
        x.no = @segments.length
        x.parent = self
        @segments << x
      else
        x.segments.each { |z| self << z}
      end
    end
      
    # add a segment to the end of the message
    def << (x)
      if x.kind_of? HL7::Segment
        x.no = @segments.length
        x.parent = self
        @segments << x
      else
        x.segments.each { |z| self << z}
      end
    end
  
    # return a Array of segments as HL7::Segment
    def segments
      @segments
    end
    
    # for testing, load and parse a file
    def self.loadfile(file)
      HL7::Message.parse(File.open(file) {|fn| fn.read})
    end
    
    # form a Message object from HL7 source
    def self.parse (text)
      msg = HL7::Message.new()
      segments = text.split("\r")
      @aegments = []
      return if segments.length == 0
      @seg_sep = "\r"
      if segments.length == 1
        # hmm, not using \r as separator, try \n
        segments = text.split("\n")
        @seg_sep = "\n"
      end
      if segments.length > 1 and segments[1][0] == "\n"
        # using \r\n evidently
        segments = text.split("\r\n")
        @seg_sep = "\r\n"
      end
      separator = segments[0][3..3]
      i = 1
      while i < segments.length
        if segments[i][0..2] == "MSH" || segments[i][0..2] == "BHS" || segments[i][0..2] == "FHS"
          separator = segments[i][3..3]
        end
        re = Regexp.new("$[A-Z][A-Z][A-Z]#{separator}.*")
        if ! segments[i] =~ re
          # assume unescaped segment separator
          segments[i-1] = segments[i-1] + '\\X0D\\' + segments[i]
          segments.delete_at i
        else
          i += 1
        end
      end # while
      # and round again
      i = 0
      seg_objects = []
      separator = segments[0][3..3]
      esc = "\\"
      subcomp_sep = "&"
      while i < segments.length
        seg_type = segments[i][0..2]
        if seg_type =~ /[A-Z][A-Z0-9][A-Z0-9]/
          if seg_type == "MSH" || seg_type == "BHS" || seg_type == "FHS"
            separator = segments[i][3..3]
            fields = segments[i].split separator
            comp_sep = fields[1][0..0]
            rep_sep = fields[1][1..1]
            if fields[1].length > 2 # some very old type HL7 don't have these chars
              esc = fields[1][2..2]
              if fields[1].length > 3
                subcomp_sep = fields[1][3..3]
              end
            end
          end
          begin
            kls = eval("HL7::#{seg_type.capitalize}")
          rescue NameError
            print "Unknown segment: #{seg_type}"
          else
            seg_obj = kls.parse(segments[i], separator, comp_sep, subcomp_sep, rep_sep, esc)
            msg << seg_obj
          end
        else
          print "Stupid segment %p ignored" % seg_type
        end
        i += 1
      end # while
      msg
    end # parse
    
    # provide direct access to the first segment of the name of the method
    def method_missing (method)
      seg_type = method.to_s.upcase
      r = Blank.new
      @segments.each do |seg|
        if seg[0].to_s == seg_type
          r = seg
        end
      end
      r
    end
    
    # iterate through all segments of type +seg_type+, starting at segment no.
    # +start+ ending with the first segment encountered of type +end_seg+
    # if all nil, iterates all segments.
    def each (seg_type, start=nil, end_seg=nil)
      start ||= 0
      while start < @segments.length and @segments[start][0] != end_seg
        if @segments[start][0].to_s == seg_type
          yield @segments[start]
        end
        start += 1
      end
    end
    
    # serialise back to HL7 format
    def to_hl7(range=nil)
      if range.nil?
        segs = @segments.map {|x| x.to_hl7}
      else
        segs = @segments[range].map {|x| x.to_hl7}
      end
      segs.join("\r")+"\r"
    end
    
    # as for to_hl7 but add MLLP marker bytes
    def to_mllp(range)
      pre_mllp = to_hl7(range)
      "\x0b" + pre_mllp + "\x1c\r"
    end

    def to_qp # to quoted-printable
      text = self.to_hl7
      line = 0
      i = 0
      len = 0
      r = ""
      while i < text.length
        if text[i] == 13
          len += 3
        else
          len += 1
        end
        if len > 79
          r << text[line..i-1].gsub("\r","=0D")+"=\r\n"
          line = i
          len = 0
        end
        i += 1
      end
      r
    end

    # called by +pp+ to do pretty-printing
    def pretty_print(pp)
      pp.group(1) do
        @segments.each do |x|
          pp.breakable
          pp.pp(x)
        end
      end
    end
    
    # pretty-print but to a string
    def to_s
      sio = StringIO.new("","w")
      old_stdout = $>
      $> = sio; pp self; $> = old_stdout
      sio.string
    end

    # the number instances of a particular segment in the message
    def number_of(seg)
      count = 0
      @segments.each {|s| count += 1 if s[0].to_s == seg}
      return count
    end

    # true if multiple MSH segments in this message
    def multi?
      return number_of("MSH")>1
    end
  
    # divide the message by its MSG segments
    def divide
      submsgs = []
      thismsg = []
      first = true
      @segments.each do |seg|
        if seg[0].to_s == "MSH"
          if first
            first = false
          else
            submsgs << HL7::Message.new(thismsg)
            thismsg = []
          end
        end
        thismsg << seg
      end
      submsgs << HL7::Message.new(thismsg)
      return submsgs
    end  

    # the number instances of a particular segment in the message
    def number_of(seg)
      count = 0
      @segments.each {|s| count += 1 if s[0].to_s == seg}
      return count
    end

    
    # form a standard MSH segment
    def standard_msh
      msh = HL7::Msh.new
      msh.segment = "MSH"
      msh.encoding_characters = '^~\\&'
      msh.sending_application = "Wedgetail"
      msh.datetime_of_message = :now
      msh.version_id = {:version_id=>"2.3.1",:internationalization_code=>{:identifier=>"AUS",:name_of_coding_system=>"ISO"},:international_version_id=>{:identifier=>"AS4700.2",:name_of_coding_system=>"L"
  }}
      msh
    end
    
    
    # form a HL7 ACK message, as a reply to this message. If +error+ is valued, a NACK will be produced with it as the error string.
    def ack(error=nil)
      ack = HL7::Message.new
      msh = ack.standard_msh
      msh.receiving_application = self.msh.sending_application
      msh.receiving_facility = self.msh.sending_facility
      msh.message_type = {:message_code=>'ACK',:trigger_event=>self.msh.message_type.trigger_event,:message_structure=>'ACK'}
      msh.processing_id = self.msh.processing_id
      msh.message_control_id = "K%X" % Time.now.to_i
      ack << msh
      msa = HL7::Msa.new
      msa.segment = "MSA"
      msa.control_id = self.msh.message_control_id
      if self.msh.accept_acknowledgement_type.blank? and self.msh.application_acknowledgement_type.blank?
        # we are using old-style ACKs
        if error
          msa.code = "AE"
          msa.text = error
        else
          msa.code = "CA"
          msa.text = "Normal acknowledgement."
        end
      else
        # we are using new-style ACKs
        ack_type = self.msh.accept_acknowledgement_type
        if error
          if ack_type == "AL" or ack_type == "ER"
            msa.code = "CE"
            msa.text = error
          else
            return nil
          end
        else
          if ack_type == "AL" or ack_type == "SU"
            msa.code = "CA"
            msa.text = "Normal acknowledgement."
          else
            return nil
          end # if ack_type
        end # if error
      end # if
      ack << msa
      return ack
    end # def
  end # class
end # module

