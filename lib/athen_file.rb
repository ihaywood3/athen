
# this is the component that interfaces with the filesystem

require 'date'
require 'hl7/message'
require 'sqlite3'
SQLite3::Database.results_as_hash = true
SQLite3::Database.type_translation = true
begin
  require 'win32/registry'
rescue
end

module Athen

  class FileManager

    def file_code
      (Time.now.to_i).to_s(36).upcase
    end

    def initalize(iface)
      @iface = iface
      @locations = []
      begin
        Win32::Registry::HKEY_CURRENT_USER.open('SOFTWARE\Athen') do |reg|
          @locations << reg['dbLocation']
        end
      rescue 
        if ENV['HOME']
          @locations << ENV['HOME']+File::Separator+'.athen.db'
        end
        # default location on UNIX
        locations << '/var/lib/athen.db'
      end
      @db = nil
      @locations.each do |x|
        begin
          if File.exists? x
            @db = SQLite3::Database.new(x)
            break
          end
        rescue
        end
      end
      unless @db
        @iface.log("Unable to find database",:panic)
        return
      end
      load_configs
    end

    def load_configs
      @cfg = {}
      @db.execute("select * from configs") do |row|
        @cfg[row['item']] = row['value']
      end
      @cfg['keyserver'] = 'hkp://subkeys.pgp.net/' unless @cfg['keyserver']
      @cfg['base'] = '/var/spool/athen/' unless @cfg['base']
      @cfg['logfile'] = '/var/log/athen.log' unless @cfg['logfile']
      @cfg['incoming'] = $cfg['base']+File::Separator+'incoming' unless @cfg['incoming']
      @cfg['outgoing'] = $cfg['base']+File::Separator+'outgoing' unless @cfg['outgoing']
      @cfg['errors'] = $cfg['base']+File::Separator+'errors' unless @cfg['errors']
      @cfg['waiting'] = $cfg['base']+File::Separator+'waiting' unless @cfg['waiting']
      @iface.open_log(@cfg['logfile'])
    end

    def config_insist(*cfgs)
      cfgs.each do |l|
        unless @cfg[l]
          @iface.log("%s config option not set" % l, :panic)
          return false
        end
      end
      return true
    end

    def config_get(item)
      return @cfg[item]
    end


    def config_save(item,value)
      @cfg[item] = value
      if @db.get_first_value("select count(*) from configs where item = ?",item) == 0
        @db.execute("insert into configs (item,value) values (?,?)", item,value)
      else
        @db.execute("update configs set value=? where item=?",value,item)
      end
    end


    def FileManager.create_db(place)
      db = SQLite3::Database.new(place)
      db.execute_batch(<<sql)
create table configs (
   item text,
   value text
);

create table outgoing (
   id integer primary key asc,
   status text,
   path text,
   last_sent integer,
   control_id text,
   no_sent integer,
   hl7 blob
);

create incoming (
   id integer primary key,
   status text,
   filename text
);
sql
      db.close
    end

    def unique_file(dir,suggested_name,suffix,no)
      # opens a new file with a guaranteed unique name, returns File object
      if suggested_name
        name = suggested_name
      else
        name = file_code
      end
      if no == 0
        path = dir+File::Separator+name+suffix
      else
        path = dir+File::Separator+name+'-'+no+suffix
      end
      begin
        return [path,File.open(path,File::CREAT|File::EXCL|File::WRONLY)] # deep UNIX magic to only create if doesn't exist
      rescue Errno::EEXIST
        return unique_file(dir,name,suffix,no+1)
      end
    end

    def write_file(dir,data,suggested_name=nil,suffix=".hl7")
      # writes data to a guaranteed unique file, returns name so chosen
      path, fd = unique_file(dir,suggested_name,suffix,0)
      fd.write(data)
      fd.close()
      @iface.log("writing file %s" % path,:info)
      return path
    end

    
    def scan_files
      @cfg['incoming'].split(';').each do |scan|
        Dir.new(scan).each do |fname|
          unless fname == '.' or fname == '..'
            fpath = scan+File::Separator+fname
            stat = File::Stat.new(fpath)
            if Time.now.to_i-stat.mtime.to_i > 60
              admit_file(fpath,File.open(fpath) { |f| f.read }) if @db.get_first_value("select count(*) from outgoing where path = ?",fpath) == 0
            end
          end
        end
      end
    end

    def admit_file(fpath,msg) # admit a file into the tracking system
      msg = msg[1..-1] if msg[1..4] == "MSG|" # some HL7 have a junk byte the start
      if msg[0..3] == "MSG|" or msg[0..3] == "FSH|" or msg[0..3] == "BHS|"
        begin
          hl7 = HL7::Message.parse(msg)
        rescue
          move_to_error(fpath)
          @iface.log("HL7 parse failed: %s: %s" % [fpath,$!],:warn)
        end
      else
        begin
          hl7 = text2hl7(msg)
        rescue
          move_to_error(fpath)
          @iface.log("text->HL7 conversion failed: %s: %s" % [fpath,$!.to_s],:warn)
          return
        end
      end
      @db.execute("insert into outgoing values (status,path,last_sent,no_sent) values ('w',?,0,0)", fpath)
      id = @db.last_insert_row_id()
      if hl7.msh.message_control_id.nil? or hl7.msh.message_control_id.to_s.length < 4
        # obviously stupid value, so make one
        hl7.msh.message_control_id = id.to_s(36).upcase
      else
        # looks reasonable, but is it unique?
        if @db.get_first_value("select count(*) from outgoing where control_id = ? and status = 'w'", hl7.msh.message_control_id) > 0
          hl7.msh.message_control_id = id.to_s(36).upcase
        end
      end
      @db.update("update outgoing set hl7=?,control_id = ? where id=?",hl7.to_s,hl7.msh.message_control_id,id)
    end

    def actual_send(mso,row)
      id = row['id']
      hl7 = HL7::Message.parse(row['hl7'])
      to = hl7.msh.receiving_facility.namespace_id
      mso.pgp_send(hl7.to_qp,to)
      when :success
        @db.execute("update outgoing set status = 'w', no_sent = no_sent+1, last_sent=? where id=? ",Time.now.to_i,id)
      when :no_key
        @iface.log("cannot find a PGP key to send to %s on file %s" % [to,row['path']],:warn)
        @db.execute("update outgoing set status = 'no-key' where id=? ",id)
      when :no_trust
        @iface.log("cannot trust %s for file %s", % [to,row['path']],:warn)
        @db.execute("update outgoing set status = 'no-trust' where id=? ",id)
      end
    end

    def sending_run(mso,all=false)
      q = "select * from outgoing where status = 'w'"
      q = q+" or status = 'no-key' or status = 'no-trust'" if all
      @db.execute(q) do |row|
        age = Time.now.to_i-row['last_sent']
        case row['no_sent']
        when 0 
          actual_send(mso,row)
        when 1
          actual_send(mso,row) if age > 3600*6
        when 2
          actual_send(mso,row) if age > 3600*18
        when 3
          if age > 3600*24*2
            hl7 = HL7::Message.parse(row['hl7'])
            to = hl7.msh.receiving_facility.to_s
            iface.log("file %s being sent to %s expired with no ACK" % [row['path'],to],:warn)
            move_to_error(row['path'])
            @db.execute("update outgoing set status='expired' where id = ? ", row['id'])
          end
        end
      end
    end

    def text2hl7(msg)
      m = {}
      body = ""
      msg.each_line do |s|
        if s ~= /$([A-Za-z\-]+)\: (.*)/
          m[$1.to_lower] = $2.rstrip
        else
          body << s+"\n"
        end
      end
      hl7 = HL7::Message.new
      msh = hl7.standard_msh
      msh.sending_facility = {:namespace_id=>@cfg['from']}
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
      pid.date_of_birth = Date.strptime(m['patient-dob'])
      pid.sex = m['patient-gender'].to_s.upcase
      #pid.patient_address = {:street=>{:street=>address_line},:city=>town,:state=>state,:postcode=>postcode}
      hl7 << pid
      obr = HL7::Obr.new
      obr[0] = "OBR"
      obr.set_id = 1
      obr.filler_order_number= {:entity_identifier=>file_code,:namespace_id=>@cfg['from']}
      #obr.principal_result_interpreter = {:name=>{:family_name=>author.family_name.upcase,:given_name=>author.given_names.upcase,:id_number=>author.id}}
      obr.universal_service_identifier = {:identifier=>"11488-4",:text=>"Consultation Note",:name_of_coding_system=>"LN"}
      hl7 << obr
      obx = HL7::Obx.new
      obx[0] = "OBX"
      obx.set_id = 1
      obx.value_type = "FT"
      obx.identifier = obr.universal_service_identifier
      obx.value = body
      obx.result_status = "F"
      hl7 << obx
      hl7
    end
  end
end
