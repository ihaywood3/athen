require 'date'
require 'base64'

# a literal HL7 string, no parsing performed.
class Literal
  attr_reader :esc, :rep_sep, :subseparator, :separator

  def self.parse(text, separator, subseparator, subsubseparator, rep_sep, esc)
    self.new(text,separator, subseparator, subsubseparator, rep_sep, esc)
  end
  
  def initialize(text,separator, subseparator, subsubseparator, rep_sep, esc)
    @text = text
    @separator = separator
    @subseparator = subseparator
    @rep_sep = rep_sep
    @esc = esc
  end
  
  def self.to_hl7(x)
    x.to_s
  end
  
  def to_s
    @text
  end
  
  
  def self.from_ruby(x)
    if x.is_a? String
      Literal.new(x,nil,nil,nil,nil,nil)
    else
      x
    end
  end
  
  def pretty_print(pp)
    pp.pp(@text)
  end
  
  def blank?
    @text.length == 0
  end
  
  def length
    @text.length
  end
end

# the initial version of this library returned nil when a field or segment didn't exist.
# this meant you had to test each step of a path into the message to make sure you didn't
# dereference nil, such as <tt>hl7.pid && hl7.pid.patient_name && hl7.pid.patient_name[0] && ...</tt>
# now this class is returned, a "nice nil" that lets you dereference it, returning itself
class Blank

  # returns the empty string
  def to_s
    ''
  end
  
  # always true
  def blank?
    true
  end
  
  def length
    0
  end
  
  # returns itself always
  def [](x)
    self
  end
  
  # returns itself always
  def method_missing(x)
    self
  end

end

# HL7 STring type
class St

  def self.parse(text, separator, subseparator, subsubseparator, rep_sep, esc)
    # strictly speaking, at this point we should scan for separators and subseparators,
    # an ingore what's beyond them, as the standard says if you encounter a split field where you expect a simple
    # one you should ignore all the other fields as it may be a future version of the standard
    # however in reality it's more likely they are unescaped, so we don't
    r = "#{esc}([A-Z0-9a-z\.]+)#{esc}"
    if esc == "\\"
      r.gsub!("\\","\\\\\\\\") # \ is the escape character for Ruby, HL7 and the regexp layer. Not pretty.
    end
    re = Regexp.new(r)
    text.gsub(re) do |match|
      case $1
        when 'F'
          '|'
        when 'S'
          '^'
        when 'T'
          '&'
        when 'R'
          rep_sep
        when 'E'
          esc
        when /X([0-9A-F]+)/
          s = $1
          s2 = ''
          while s.length > 1
            s2 << s[0..1].to_i(16)
            s = s[2..-1]
          end
          s2
        when /XO([0-9A-F])/
          # an Argus special code, not in standard
          "" << $1.to_i(16)
        when '.br'
          "\n"
        else
          ""
      end # case
    end # do 
  end # def
  
  # escapes common to all string types
  def self.common_to_hl7(string)
    string  = string.to_s unless string.kind_of? String
    string = string.gsub('|','\\F\\')
    string.gsub!('^','\\S\\')
    string.gsub!('&','\\T\\')
    string.gsub!('\\','\\E\\')
    string.gsub!("\r","")
    string
  end
  
  def self.to_hl7(string)
    common_to_hl7(string).gsub("\n",'\\X0D0A\\')
  end
  
  def self.from_ruby(x)
    x
  end
end

# "hierarchic designator"
class Hd < HL7::Field 
  def fields_desc
    [
      [:namespace_id,false,Is],
      [:universal_id,false,St],
      [:universal_id_type,false,Id]
    ]
  end
end

# encapsulated data
class Ed < HL7::Field 
  def fields_desc
    [
      [:source,false,Hd],
      [:data_type,false,Id],
      [:subtype,false,Id],
      [:encoding,false,Id],
      [:data,false,Tx]
    ]
  end
  
  # override to deal with HL7 encoding logic
  def data
    case get(:encoding)
      when 'A'
        get(:data)
      when /Hex/i
        s2 = ''
        i = 0
        s = get(:data)
        while i < s.length
          s2 << s[i..i+1].to_i(16)
          i+=2
        end
        s2
      when /Base64/i
        Base64.decode64(get(:data))
    end
  end
end

# processing type
class Pt < HL7::Field
  def fields_desc
    [
      [:processing_id,false,Id],
      [:processing_mode,false,Id]
    ]
  end
end

# identifier for locally-defined tables
class Is < St
end

# identifier for centrally-defined tables
class Id < St
end

# text
class Tx < St
end

# formatted string
class Ft < St
  # override for extra escape types
  def self.to_hl7(string)
    string = common_to_hl7 string
    string.gsub!("\n","\\.br\\")
    string
  end
end

# version ID
class Vid < HL7::Field 
  def fields_desc
    [
      [:version_id,false,Id],
      [:internationalization_code,false,Ce],
      [:international_version_id,false,Ce]
    ]
  end
end

# coded entity
class Ce < HL7::Field 
  def fields_desc
    [
      [:identifier,false,St],
      [:text,false,St],
      [:name_of_coding_system,false,Id],
      [:alternate_identifer,false,St],
      [:alternate_text,false,St],
      [:alternate_name_of_coding_system,false,Id]
    ]
  end
  
  # so that we work nicely with case..when,
  # compares on either +identifier+ or +alternative_identifier+
  def ===(x)
    return @fields[0] == x || @fields[3] == x
  end
end

class Cx < HL7::Field
  def fields_desc
    [
      [:id_number,false,St],
      [:check_digit,false,St],
      [:check_digit_scheme,false,Id],
      [:assigning_authority,false,Hd],
      [:identifier_type_code,false,Id],
      [:assigning_facility,false,Hd],
      [:effective_date,false,DateTime],
      [:expiration_date,false,DateTime],
      [:assigning_jurisdiction,false,Cwe],
      [:assigning_agency,false,Cwe]
    ]
  end
end

# coded with exceptions 
class Cwe < HL7::Field
  def fields_desc
    [
      [:identifer,false,St],
      [:text,false,St],
      [:name_of_coding_system,false,Id],
      [:alternate_identifer,false,St],
      [:alternate_text,false,St],
      [:alternate_name_of_coding_system,false,Id],
      [:coding_system_version_id,false,St],
      [:alternate_coding_system_version_id,false,St],
      [:original_text,false,St]
    ]
  end
end

# eXtended Personal Name
class Xpn < HL7::Field
  def fields_desc
    [
      [:family_name,false,Fn],
      [:given_name,false,St],
      [:second_name,false,St],
      [:suffix,false,St],
      [:prefix,false,St],
      [:degree,false,Is],
      [:name_type_code,false,Id],
      [:name_representation_code,false,Id],
      [:name_context,false,Ce],
      [:name_validity_range,false,DrAsSubfield],
      [:name_assembly_order,false,Id],
      [:effective_date,false,Ts],
      [:expiration_date,false,Ts],
      [:professional_suffix,false,St]
    ]
  end
end

# family name
class Fn < HL7::Field
  def fields_desc
    [
      [:surname,false,St],
      [:own_surname_prefix,false,St],
      [:own_surname,false,St],
      [:spouse_surname_prefix,false,St],
      [:spouse_surname,false,St]
    ]
  end
  
  def to_s
    @fields[0]
  end
end

# numeric
class Nm 
  def self.parse(text, separator, subseparator, subsubseparator, rep_sep, esc)
    text.to_f
  end
  
  def self.to_hl7(number)
    number.to_s
  end
  
  def self.from_ruby(x)
    x
  end
end

# numeric integer
class Si 
  def self.parse(text, separator, subseparator, subsubseparator, rep_sep, esc)
    text.to_i
  end
  
  def self.to_hl7(number)
    number.to_s
  end
  
  def self.from_ruby(x)
    x
  end
end


# structured numeric
class Sn < HL7::Field
  def fields_desc
    [
     [:comparator,false,St],
     [:num1,false,Nm],
     [:separator_suffix,false,St],
     [:num2,false,Nm]
    ]
  end
end

class MessageType < HL7::Field
  def fields_desc
    [
      [:message_code,false,Id],
      [:trigger_event,false,Id],
      [:message_structure,false,Id]
    ]
  end
end

# entity
class Ei < HL7::Field
  def fields_desc
    [
      [:entity_identifier,false,St],
      [:namespace_id,false,Is],
      [:universal_id,false,St],
      [:universal_id_type,false,Id]
    ]
  end
end

class Eip < HL7::Field
  def fields_desc
    [
      [:placer,false,Ei],
      [:filler,false,Ei]
    ]
  end
end

# timing-quantity
class Tq < HL7::Field
  def fields_desc
    [
      [:quantity,false,Cq],
      [:interval,false,Ri],
      [:duration,false,St],
      [:start,false,Ts],
      [:end,false,Ts],
      [:priority,false,St],
      [:condition,false,St],
      [:text,false,Tx],
      [:conjunction,false,Id],
      [:order_sequencing,false,Osd],
      [:occurrence_duration,false,Ce],
      [:total_occurrences,false,Nm]
    ]
  end
end

class Osd < HL7::Field
  def fields_desc
    [
      [:sequence_flag,false,Id],
      [:placer_entity_identifier,false,St],
      [:placer_namespace_id,false,H7::Is],
      [:filler_entity_identifier,false,St],
      [:filler_namespace_id,false,Is],
      [:sequence_condition_value,false,St],
      [:max_repeats,false,Nm],
      [:placer_universal_id,false,St],
      [:placer_universal_id_type,false,Id],
      [:filler_universal_id,false,St],
      [:filler_universal_id_type,false,Id]
    ]
  end
end

class Cq < HL7::Field
  def fields_desc
    [
      [:quantity,false,Nm],
      [:units,false,St] # LAMESPEC: supposed to be CE but this becomes unparseable
    ]
  end
end

class Ri < HL7::Field
  def fields_desc
    [
      [:repeat_pattern,false,Is],
      [:explicit_time_interval,false,St]
    ]
  end
end


class Xon < HL7::Field
  def fields_desc
    [
      [:organisation_name,false,St],
      [:name_type_code,false,Is],
      [:id,false,St], # should be NM, but not actually a float
      [:check_digit,false,St],
      [:check_digit_scheme,false,Id],
      [:assigning_authority,false,Hd],
      [:identifier_type_code,false,Id],
      [:assigning_facility,false,Hd],
      [:name_representation_code,false,Id],
      [:organization_identifier,false,St]
    ]
  end
end

class HL7DateTime
  def self.parse(text, separator, subseparator, subsubseparator, rep_sep, esc)
    if /([0-9\.]+)([+\-][0-9]+)/ =~ text
      text = $1
      if $2.length == 5
        tz = (($2[1..2].to_i*60)+$2[3..4].to_i)/1440.0
        if $2[0..0] == "-"
          tz = -tz
        end
      else
        tz = 0
      end
    else
      tz = 0
    end
    if /([0-9]+)(\.[0-9]+)/ =~ text
      text = $1
      second = $2.to_f
    else
      second = 0
    end
    year = text[0..3].to_i
    if text.length >= 6
      month = text[4..5].to_i
    else
      month = 1
    end
    if text.length >= 8
      day = text[6..7].to_i
    else
      day = 1
    end
    if text.length >= 10
      hour = text[8..9].to_i
    else
      hour = nil
    end
    if text.length >= 12
      minute = text[10..11].to_i
    else
      minute = 0
    end
    if text.length >= 14
      second += text[12..13].to_i
    else
      second = 0
    end
    if hour.nil?
      return Date.civil(year,month,day)
    else
      second = Rational((second*1000).round,1000) # convert to Rational
      return DateTime.civil(year,month,day,hour,minute,second,tz)
    end
  end
  
  def self.to_hl7(dt)
    case dt
    when DateTime
      x = dt.strftime "%Y%m%d%H%M%S"
      of = dt.offset()*1440
      x << "%+.2d%.2d" % [of/60,of.abs%60]
    when Date
      x = dt.strftime "%Y%m%d"
    when Time
      x = dt.strftime "%Y%m%d%H%M%S"
      x << "%+.2d%.2d" % [dt.gmt_offset/3600,(dt.gmt_offset.abs % 3600) / 60]
    when :now,'now'
      dt = Time.now
      x = dt.strftime "%Y%m%d%H%M%S"
      x << "%+.2d%.2d" % [dt.gmt_offset/3600,(dt.gmt_offset.abs % 3600) / 60]
    end
    return x
  end
  
  def self.from_ruby(x)
    x
  end
  
end

class Ts < HL7::Field
  def fields_desc
   [
      [:time,false,HL7DateTime],
      [:degree_of_precision,false,Id]
    ]
  end
  
  def strftime(x="%c")
    time.strftime x
  end
  
  def self.from_ruby(x)
    x = {:time=>x} unless x.kind_of? Hash
    super x
  end
  
  def pretty_print(pp)
    pp.text(strftime)
  end
end

# the HL7 standard states that DR cannot be used as a subfield
# and then does 20 pages later!
# with this type we assume the sender has not used the degree_of_precision subcomponent
# (which is the only way in which this type is parseable)
class DrAsSubfield < HL7::Field

  def fields_desc
   [
      [:start_time,false,HL7DateTime],
      [:end_time,false,HL7DateTime]
    ]
  end
end

class Dr < HL7::Field
  def fields_desc
    [
      [:start_time,false,Ts],
      [:end_time,false,Ts]
    ]
  end
end

# eXtended Address
class Xad < HL7::Field
  def fields_desc
    [
      [:street,false,Sad],
      [:other_designation,false,St],
      [:city,false,St],
      [:state,false,St],
      [:postcode,false,St],
      [:country,false,Id],
      [:address_type,false,Id],
      [:other_geographic_designation,false,St],
      [:county,false,Is],
      [:census_tract,false,Is],
      [:address_representation_code,false,Id],
      [:address_validity_range,false,DrAsSubfield],
      [:effective_date,false,Ts],
      [:expiration_date,false,Ts]
    ]
  end
end

# Street ADress
class Sad < HL7::Field
  def fields_desc
    [
      [:street,false,St],
      [:name,false,St],
      [:dwelling_number,false,St]
    ]
  end
  
  def to_s
    if @fields[0].nil?
      "%s %s" % [@fields[2],@fields[1]]
    elsif @fields[1].nil? && @fields[2].nil?
      @fields[0]
    else
      "%s\n %s %s" % [@fields[0] || '',@fields[1] || '',@fields[2] || '']
    end
  end
end

# eXtended Telephone Number
class Xtn < HL7::Field
  def fields_desc
    [
      [:telephone,false,St],
      [:use_code,false,Id],
      [:equipment_type,false,Id],
      [:email,false,St],
      [:country_code,false,St],
      [:area_code,false,St],
      [:local_number,false,St],
      [:extension,false,St],
      [:any_text,false,St],
      [:extension_prefix,false,St],
      [:speed_dial_code,false,St],
      [:unformatted_telephone_number,false,St]
    ]
  end
  
  def to_s
    if @fields[0]
      @fields[0]
    else
      "%s%s%s%s" % [@fields[4]||'',@fields[5]||'',@fields[6]||'',@fields[7]||'']
    end
  end
end

# Place
class Pl < HL7::Field
  def fields_desc
    [
      [:point_of_care,false,Is],
      [:room,false,Is],
      [:bed,false,Is],
      [:facility,false,Hd],
      [:location_status,false,Is],
      [:person_location_type,false,Is],
      [:building,false,Is],
      [:floor,false,Is],
      [:location_description,false,St],
      [:comphrensive_location_identifier,false,Ei],
      [:assigning_authority_for_location,false,Hd]
    ]
  end
end


class Xcn < HL7::Field
  def fields_desc
    [
      [:id_number,false,St],
      [:family_name,false,Fn],
      [:given_name,false,St],
      [:second_name,false,St],
      [:suffix,false,St],
      [:prefix,false,St],
      [:degree,false,Is],
      [:source_table,false,Is],
      [:assigning_authority,false,Is],
      [:name_type_code,false,Id],
      [:identifier_check_digit,false,St],
      [:check_digit_scheme,false,Id],
      [:identifier_type_code,false,Id],
      [:assigning_facility,false,Hd],
      [:name_representation_code,false,Id],
      [:name_context,false,Ce],
      [:name_validity_range,false,DrAsSubfield],
      [:name_assembly_order,false,Id],
      [:effective_date,false,Ts],
      [:expiration_date,false,Ts],
       [:professional_suffix,false,St],
      [:assigned_jurisdiction,false,Cwe],
      [:assigning_agency,false,Cwe]
    ]
  end
end

# MOney
class Mo < HL7::Field
  def fields_desc
    [
      [:quantity,false,Nm],
      [:denomination,false,Id]
    ]
  end
end

class Moc < HL7::Field
  def fields_desc
    [
      [:money,false,Mo],
      [:charge_code,false,Ce]
    ]
  end
end

class Ndl < HL7::Field
  def fields_desc
    [
      [:name,false,Cnn],
      [:start,false,Ts],
      [:end,false,Ts],
      [:point_of_care,false,Is],
      [:room,false,Is],
      [:bed,false,Is],
      [:facility,false,Hd],
      [:location_status,false,Is],
      [:patient_location_type,false,Is],
      [:building,false,Is],
      [:floor,false,Is]
    ]
  end
end

class Cnn < HL7::Field
  def fields_desc
    [
      [:id_number,false,St],
      [:family_name,false,St],
      [:given_name,false,St],
      [:second_name,false,St],
      [:suffix,false,St],
      [:prefix,false,St],
      [:degree,false,Is],
      [:source_table,false,Is],
      [:namespace_id,false,Is],
      [:universal_id,false,St],
      [:universal_id_type,false,Id]
    ]
  end
end

# Specimen type
class Sps < HL7::Field
  def fields_desc
    [
      [:specimen_source,false,Cwe],
      [:additives,false,Cwe],
      [:specimen_collection_method,false,Tx],
      [:body_site,false,Cwe],
      [:site_modifier,false,Cwe],
      [:collection_method_modifier,false,Cwe],
      [:specimen_role,false,Cwe]
    ]
  end
end

class Prl < HL7::Field
  def fields_desc
    [
      [:parent_obx3,false,Ce],
      [:parent_obx4,false,St],
      [:parent_obx5,false,Tx]
    ]
  end
end

# so we identify this very special type in Obx
class Obx5 < Literal
end

# composite in PRD-7 - composite is a "catch-all" complex field, here we
# define for this context only to provide meaningful field names
class Prd7 < HL7::Field
  def fields_desc
    [
      [:id_number,false,St],
      [:type_id_number,false,Is],
      [:other_info,false,St]
    ]
  end
end
