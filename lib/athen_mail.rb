require 'net/smtp'
require 'net/imap'
require 'net/pop'
require 'base64'
require 'rubygems'
require 'mail'
require 'gpg'

module Athen

  class MailManager

    def initalize(iface,fso)
      @fso = fso
      @iface = iface
      Mail.defaults do
        params = {:address=> @fso.get_config('smtp_server'),:port=>25}
        if @fso.get_config('smtp_username')
          params[:user_name] = @fso.get_config('smtp_username')
          params[:password] = @fso.get_config('smtp_password'),
          params[:authentication] = 'plain'
          params[:enable_starttls_auto] = true
        end
        delivery_method :smtp, params
      end
    end

    def pgp_send(data,to,mime="application/edi-hl7")
      gpg = GPG.new(@fso.config_get('gpg-path'))
      crypted = gpg.encrypt_sign(m2,to)
      m2 = Mail.deliver do 
        body crypted
        content_type("application/pgp-encrypted")
        to to
        headers {"X-Original-MIME"=>mime}
        from @fso.get_config('from')
        subject "Encrypted message"
      end
    end

    def pgp_decrypt(mailtext)
      m = nil
      begin
        m = Mail.new(mailtext)
      rescue
        @iface.log("unable to parse e-mail: #{$!}",:error)
        return
      end
      if m.bounced?
        # process bounce message
      else
        unless m.content_type == 'application/pgp-encrypted'
          @iface.log('not an encrypted message #{m.message_id}',:error)
          @fso.write_file_error(mailtext,".eml")
          return
        end
        err = nil
        result = nil
        gpg = GPG.new(@fso.config_get('gpg-path'))
        begin
          result = gpg.decrypt_verify(m.body)
        rescue
        end
        if result[:key_id].nil?
          log("could  not identify signature",:error)
          err = "could not identify signature"
              
      end
      log "message signed by key %s" % result[:key_id]
    rescue GPGError
      error_email($!.message)
      code = save_file($cfg['waiting'],suffix=".eml",mode='')
      path = $cfg['waiting']+File::Separator+code+".eml"
      File.open(path) {|f| f.write mailtext}
      log("can't decrypt, message written to #{path}")
      return
    end
    body = nil
    begin
      m3 = TMail::Mail.parse(result[:plaintext])
      if m3.multipart?
        m3.parts.each do |p|
          if p.disposition == 'attachment' # look for the packet marked as an attachment
            body = p.body
            filename = p['Content-Disposition'].params['filename']
          end
        end
        if body.nil?
          body = m3.parts[0].body # Ok, just try with the first MIME packet
        end
      else
        body = m3.body
      end
    rescue TMail::SyntaxError # OK, don't bother parsing as e-mail at all
      body = result[:plaintext]
    end
    # now try to parse HL7
    hl7 = nil
    err = nil
    begin
      hl7 = HL7::Message.parse(body)
      filename = hl7.msh.message_control_id unless filename
    rescue HL7::Error
      err7 = "HL7 parse error: %s. No ACK will be generated" % $!.to_s
      error_email(err7,nil)
      log(err7)
    end
    if hl7 and hl7.is_ack? # it's an ACK, consume it
      process_ack(hl7.msa.control_id)
    else
      # actually write file
      begin
        code = unique_file($cfg['outgoing'],filename,mode='')
        path = $cfg['outgoing']+File::Separator+code+".hl7"
        File.open(path,"w") {|f| f.write body }
        log("messaged received and written to %s" % path)
      rescue
        err = "error writing file %s" % $!.to_s
        error_email(err,nil)
        log(err)
      end
      if hl7
        reply = hl7.ack err # when err=nil we generate a "good" ACK
        reply.msh.sending_facility = {:namespace_id=>$cfg['from']}
        pgp_create(reply.to_qp,m1['from'])
        log("ACK sent using code %s" % hl7.msh.message_control_id)
      end
    end
  end




  def receive_mails_pop
    return unless @fso.config_insist('imap_host','imap_user','imap_password')
    pop = Net::POP3.new(@fso.config_get('imap_host'))
    pop.start(@fso.get_cig('imap_user'),@fso.config_get('imap_password'))
    pop.each_mail do |m|
      pgp_decrypt(m.pop)
      m.delete
    end
  end

  def receive_mails_imap
    return unless @fso.config_insist('imap_host','imap_user','imap_password')
    failures = 0
    cont = false
    loop do
      begin
        imap = Net::IMAP.new(@fso.config_get('imap_host'))
        imap.login(@fso.config_get('imap_user'), @fso.config_get('imap_password'))
        imap.select('INBOX')
        p imap.capability
        failures = 0
        @iface.log("Logged on to #{@fso.config_get('imap_host')}",:info)
        loop do
          imap.search(["NOT", "DELETED"]).each do |message_id|
            @iface.log("Fetching message #{message_id}...")
            puts imap.fetch(message_id, "RFC822")[0].attr["RFC822"]
            imap.store(message_id, "+FLAGS", [:Deleted])
          end
          cont = true
          while cont
            idler = Thread.new(Thread.current) do |parent|
              begin
                @iface.log("inside the idler thread",:data)
                imap.idle do |resp|
                  @iface.log("the response name is #{resp.name}",:info)
                  if resp.kind_of?(Net::IMAP::UntaggedResponse) and resp.name == "EXISTS"
                    cont = false
                    imap.idle_done
                    parent.run
                  end
                end
              rescue
                @iface.log("ERROR2:%s %s" % [$!.to_s,$!.backtrace],:error)
              end
            end
            @iface.log("sleeping...",:data)
            sleep 900 # main thread sleeps for 15mins
            @iface.log("stopping idler",:data)
            idler.kill
            if cont
              # timer has expired
              imap.idle_done
              @iface.log("running NOOP",:data)
              imap.noop
            end
          end
        end  
      rescue
        failures += 1
        begin
          imap.logout()
          imap.disconnect()
        rescue
        end
        @iface.log("***ERROR:**: %s %s" % [$!.to_s,$!.backtrace],:error)
        case failures
          when 1 then sleep 10
          when 2 then sleep 30
          when 3 then sleep 600
          when 4 then sleep 600
          when 5 then sleep 900
          else sleep 1200
        end
      end
    end
  end

end
