
# this is the component that interfaces with the filesystem

require 'date'
require 'hl7/message'

module Athen

def Athen.file_code
  (Time.now.to_i-1222819200).to_s(36)
end

def Athen.setup(iface)
  $cfg = {}
  cfgs = ['/etc/athen.conf','C:\\ATHEN.INI','C:\\Program Files\\Athen\\Athen.ini','athen.conf','ATHEN.INI']
  if ENV['HOME']
    cfgs << ENV['HOME']+File::Separator+'.athen.conf'
  end
  cfgs.each {|c| config_file(c)}
  $cfg['keyserver'] = 'hkp://subkeys.pgp.net/' unless $cfg['keyserver']
  $cfg['base'] = '/var/spool/athen/' unless $cfg['base']
  $cfg['logfile'] = '/var/log/athen.log' unless $cfg['logfile']
  $cfg['incoming'] = $cfg['base']+File::Separator+'incoming' unless $cfg['incoming']
  $cfg['outgoing'] = $cfg['base']+File::Separator+'outgoing' unless $cfg['outgoing']
  $cfg['errors'] = $cfg['base']+File::Separator+'errors' unless $cfg['errors']
  $cfg['waiting'] = $cfg['base']+File::Separator+'waiting' unless $cfg['waiting']
  iface.logfile = File.open($cfg['logfile'],'a')
end

def Athen.config_file(cfg)
  if File.exists? cfg
    File.open(cfg).each_line do |l|
      case l
        when /^#.*/ then nil
        when /(.*)=(.*)/ then $cfg[$1.strip] = $2.strip
      end
    end
  end
end

def Athen.config_insist(iface, *cfgs)
  cfgs.each do |l|
    unless $cfg[l]
      iface.log("%s config option not set" % l)
      iface.panic("Not Configured")
    end
  end
end


def Athen.unique_file(dir,suggested_name=nil,suffix=".hl7",mode="?")
  code = file_code()
  if suggested_name
    name = suggested_name
  else
    name = code+"0"
  end
  path = dir+File::Separator+name+mode+suffix
  no = 0
  while Dir.glob(path).length > 0
    no += 1
    name = code+no.to_s
    path = dir+File::Separator+name+mode+suffix 
  end
  return name
end

def Athen.scan_files
  $cfg['incoming'].split(';').each do |scan|
    Dir.new(scan).each do |fname|
      unless fname == '.' or fname == '..'
        fpath = scan+File::Separator+fname
        stat = File::Stat.new(fpath)
        if Time.now.to_i-stat.mtime.to_i > 60
          process_file(fpath,File.open(fpath) { |f| f.read })
          File.unlink(fpath)
        end
      end
    end
  end
end


def Athen.process_file(iface,fpath,msg)
  if msg[0..3] == "MSG|" or msg[0..3] == "FSH|" or msg[0..3] == "BHS|"
    begin
      hl7 = HL7::Message.parse(msg)
    rescue
      iface.log("HL7 parse failed: %s: %s" % [fpath,$!])
    end
  else
    begin
      hl7 = text2hl7(msg)
    rescue
      iface.log("text->HL7 conversion failed: %s: %s" % [fpath,$!.to_s])
      return
    end
  end
  code = unique_file($cfg['waiting'])
  hl7.msh.message_control_id = code
  actual_send(hl7)
end

def Athen.actual_send(iface,hl7)
  to = hl7.msh.receiving_facility.namespace_id
  fpath = case pgp_create(hl7.to_qp,to)
    when :success then $cfg['waiting']+File::Separator+code+"0.hl7"
    when :no_key then $cfg['errors']+File::Separator+".hl7"
    when :no_trust then $cfg['waiting']+File::Separator+"x.hl7"
  end
  begin 
    File.open(fpath,"w") {|f| f.write hl7.to_hl7 }
    iface.log("wrote message to %s" % fpath)
  rescue
    iface.log("error writing to %s: %s" % [fpath,$!.to_s])
    iface.panic("cannot write to directory %s" % fpath)
  end
end

def Athen.resend(iface)
  Dir.glob($cfg['waiting']+File::Separator+"*.hl7") do |fname|
    fname =~ /(.*)(.)\.hl7$/
    stat = File::Stat.new fname
    age = Time.now.to_i-stat.mtime.to_i
    case $2
      when "0" 
        resend_file(fname,$1+"1.hl7") if age > 3600
      when "1"
        resend_file(fname,$1+"2.hl7") if age > 3600*6
      when "2"
        resend_file(fname,$1+"3.hl7") if age > 3600*24
      when "3"
        if age > 3600*2
	  s = File.new(fname) {|f| f.read }
          hl7 = HL7::Message.parse(s)
          File.unlink(fname)
          to = hl7.msh.receiving_facility.to_s
          iface.log("file %s to %s expired with no ACK" % [fname,to])
	  File.new($cfg['errors']+File::Separater+$1,"w") {|f| f.write s}
        end
    end
  end
end

def Athen.resend_trust
  Dir.glob($cfg['waiting']+File::Separator+"*x.hl7") do |fname|
    hl7 = HL7::Message.parse(File.new(fname) {|f| f.read })
    File.unlink(fname)
    actual_send(hl7)
  end
end

def Athen.resend_file(oldfile,newfile)
  s = File.new(oldname) {|f| f.read}
  File.new($cfg['waiting']+File::Separater+newfile,"w") {|f| f.write s}
  hl7 = HL7::Message.parse(s)
  File.unlink(oldname)
  to = hl7.msh.receiving_facility.namespace_id
  pgp_create(hl7.to_qp,to)
end


def Athen.text2hl7(msg)
  m = TMail::Mail.parse(msg)
  hl7 = HL7::Message.new
  msh = hl7.standard_msh
  msh.sending_facility = {:namespace_id=>$cfg['from']}
  msh.message_type = {:message_code=>'ORU',:trigger_event=>'R01'}
  msh.processing_id = {:processing_id=>'P'}
  msh.receiving_facility = {:namespace_id=>m.to[0]}
  hl7 << msh
  pid = HL7::Pid.new
  pid[0] = "PID"
  pid.set_id = 1
  pil = []
  if m['wedgetail-number']
    pil << {:id_number=>m['wedgetail-number'].to_s,:identifier_type_code=>"WEDGIE",
      :assigning_authority=>{:namespace_id=>"Wedgetail",:universal_id=>'wedgetail.medicine.net.au',:universal_id_type=>'DNS'},
      :assigning_facility=>{:namespace_id=>"Wedgetail",:universal_id=>'wedgetail.medicine.net.au',:universal_id_type=>'DNS'}}
  end
  if m['medicare']
    pil << {:id_number=>m['medicare'].to_s,:identifier_type_code=>"MC",:assigning_authority=>{:namespace_id=>"AUSHIC"}}
  end
  pid.patient_identifier_list = pil
  first, second = m['patient-given-names'].to_s.upcase.split(" ",2)
  pid.patient_name = {:family_name=>{:surname=>m['patient-family-name'].to_s.upcase},:given_name=>first,:second_name=>second}
  pid.date_of_birth = Date.strptime(m['patient-dob'].to_s)
  pid.sex = m['patient-gender'].to_s.upcase
  #pid.patient_address = {:street=>{:street=>address_line},:city=>town,:state=>state,:postcode=>postcode}
  hl7 << pid
  obr = HL7::Obr.new
  obr[0] = "OBR"
  obr.set_id = 1
  obr.filler_order_number= {:entity_identifier=>file_code,:namespace_id=>$cfg['from']}
  #obr.principal_result_interpreter = {:name=>{:family_name=>author.family_name.upcase,:given_name=>author.given_names.upcase,:id_number=>author.id}}
  obr.universal_service_identifier = {:identifier=>"11488-4",:text=>"Consultation Note",:name_of_coding_system=>"LN"}
  hl7 << obr
  obx = HL7::Obx.new
  obx[0] = "OBX"
  obx.set_id = 1
  obx.value_type = "FT"
  obx.identifier = obr.universal_service_identifier
  obx.value = m.body
  obx.result_status = "F"
  hl7 << obx
  hl7
end

end