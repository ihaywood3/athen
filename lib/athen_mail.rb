require 'net/smtp'
require 'net/imap'
require 'net/pop'
require 'net/imap'
require 'base64'
require 'rubygems'
#require 'tmail'
require 'gpg'

module Athen
  def Athen.pgp_create(m,to)
    gpg = GPG.new
    signature= gpg.sign(m)
    signature.gsub!("\n","\r\n")
    boundary = Base64.encode64(Time.now.to_s).strip
    boundary1 = "inner"+boundary
    m2 = <<EOF
Content-Type: multipart/signed;\r
  boundary="#{boundary1}";\r
  protocol="application/pgp-signature";\r
  micalg=pgp-sha1\r
\r
--#{boundary1}\r
Content-Type: application/edi-hl7\r
Content-Transfer-Encoding: quoted-printable\r
\r
#{m}\r
--#{boundary1}\r
Content-Type: application/pgp-signature; name=signature.asc\r
Content-Description: This is a digitally signed message part.\r
\r
#{signature}\r
--#{boundary1}--\r
EOF
    begin
      crypted = gpg.encrypt(m2,to).gsub(/([^\r])\n/,"\\1\r\n")
    rescue GPGError
      error_email($!.message,nil)
      log("message not sent due to GPG error") 
      return :no_key
    end
    m3 = TMail::Mail.new
    boundary2 = "outer"+boundary
    m3.body = <<EOF2
--#{boundary2}\r
Content-Type: application/pgp-encrypted\r
Content-Disposition: attachment\r
\r
Version: 1\r
--#{boundary2}\r
Content-Type: application/octet-stream\r
Content-Disposition: inline; filename="msg.asc"\r
\r
#{crypted}\r
--#{boundary2}--\r
EOF2
    m3.set_content_type('multipart','encrypted',{'boundary'=>boundary2,'protocol'=>'application/pgp-encrypted'})
    m3['to'] = to
    m3['from'] = $cfg['from']
    m3['date'] = Time.new.strftime "%a, %e %b %Y, %H:%m:%S  %z"
    m3['subject'] = "Encrypted message"
    send_email(m3,to)
    return :success
  end

  def Athen.pgp_decrypt(mailtext)
    pgp = false
    body = nil
    begin
      m1 = TMail::Mail.parse(mailtext)
      if m1.multipart? 
        m1.parts.each do |part|
          if part.content_type == 'application/octet-stream'
            body = part.body
          end
          if part.content_type == 'application/pgp-encrypted'
            pgp = true
            log "identified PGP-MIME"
          end
        end
      else
        body = m1.body
      end
    rescue TMail::SyntaxError
      error_email("Unable to parse message",mailtext)
      return
    end
    unless pgp
      a = mailtext =~ /-----BEGIN PGP MESSAGE-----/
      if a
        b = (mailtext =~ /-----END PGP MESSAGE-----/)+25
        body = mailtext[a..b]
        log "Using inline PGP"
      else
        error("Unable to find PGP text")
        error_email("Unable to find PGP text",m1)
        return
      end
    end
    gpg = GPG.new
    filename = nil
    begin
      result = gpg.decrypt_verify(body)
      if result[:key_id].nil?
        begin
          m2 = TMail::Mail.parse(body)
        rescue TMail::SyntaxError
          error_email("Unable to parse decrypted contents",m1)
          return
        end
        msg = m2.parts[0].body
        if m2.parts[0]['Content-Disposition'] and m2.parts[0]['Content-Disposition'].params['filename']
          filename = m2.parts[0]['Content-Disposition'].params['filename']
        end
        sig = m2.parts[1].body
        result = gpg.verify(msg,sig)
      end
      if result[:key_id].nil?
        error_email("Unable to identify signature",m1)
        log("could  not identify signature")
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
        reply = hl7.ack err # when err=nil we generate a "good" AXK
        reply.msh.sending_facility = {:namespace_id=>$cfg['from']}
        pgp_create(reply.to_qp,m1['from'])
        log("ACK sent using code %s" % hl7.msh.message_control_id)
      end
    end
  end


  def Athen.error_email(message,attachment=nil)
    m = TMail::Mail.new
    if attachment
      boundary = Base64.encode64(Time.now.to_s).strip
      m.set_content_type('multipart','mixed',{'boundary'=>boundary})
      m.body = <<EOF4
--#{boundary}\r
Content-Type: text/plain\r
Content-Transfer-Encoding: quoted-printable\r
Content-Disposition; inline\r
\r
#{message}\r
--#{boundary}\r
Content-Type: message/rfc822; name=email\r
Content-Disposition: attachment; filename=email\r
\r
#{attachment.to_s}\r
\r
--#{boundary}--\r
EOF4
    else
      m.set_content_type('text','plain')
      m.body = message
    end
    m['mime-version'] = '1.0'
    m['to'] = $cfg['error_report']
    m['from'] = $cfg['from']
    m['subject'] = 'Wedgechick Error'
    m['date'] = Time.new.strftime("%a, %e %b %Y, %H:%m:%S  %z")
    send_email(m,$cfg['errors'])
  end

  def Athen.send_email(mail, to)
    config_insist('smtp','from','error_report')
    Net::SMTP.start($cfg['smtp'],25) do |smtp|
      smtp.send_message mail, to, $cfg['from'] 
    end
  end


  def Athen.receive_mails_pop
    config_insist('imap_host','imap_user','imap_password')
    pop = Net::POP3.new($cfg['imap_host'])
    pop.start($cfg['imap_user'],$cfg['imap_password'])
    pop.each_mail do |m|
      pgp_decrypt(m.pop)
      m.delete
    end
  end

  def Athen.receive_mails_imap(iface)
    config_insist(iface,'imap_host','imap_user','imap_password')
    failures = 0
    cont = false
    loop do
      begin
        imap = Net::IMAP.new($cfg['imap_host'])
        imap.login($cfg['imap_user'], $cfg['imap_password'])
        imap.select('INBOX')
        p imap.capability
        failures = 0
        iface.log("Logged on to #{$cfg['imap_host']}")
        loop do
          imap.search(["NOT", "DELETED"]).each do |message_id|
            iface.log("Fetching message #{message_id}...")
            puts imap.fetch(message_id, "RFC822")[0].attr["RFC822"]
            imap.store(message_id, "+FLAGS", [:Deleted])
          end
          cont = true
          while cont
            idler = Thread.new(Thread.current) do |parent|
              begin
                iface.log("inside the idler thread")
                imap.idle do |resp|
                  puts "the response name is #{resp.name}"
                  if resp.kind_of?(Net::IMAP::UntaggedResponse) and resp.name == "EXISTS"
                    cont = false
                    imap.idle_done
                    parent.run
                  end
                end
              rescue
                puts "ERROR2:%s %s" % [$!.to_s,$!.backtrace]
              end
            end
            iface.log("sleeping...")
            sleep 900 # main thread sleeps for 15mins
            iface.log("stopping idler")
            idler.kill
            if cont
              # timer has expired
              imap.idle_done
              iface.log("running NOOP")
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
        iface.log("***ERROR:**: %s %s" % [$!.to_s,$!.backtrace])
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
