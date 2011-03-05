require 'tmpdir'
require 'date'

class GPGError < StandardError
  attr :message
  def initialize(message)
    @message = message
  end
end

class WrongKey < GPGError
  def initialize
    @message = <<EOF9
FROM has tried to send you a message using the
wrng public key, so you couldn't decrypt it.
Please ask them to end it again with the 
correct key
EOF9
  end
end

class NoPubKey < GPGError
  def initialize(key)
    @message = <<EOF10
En/decryptioncould not occur because a public key for
   
   #{key}

could not be found on the keyservers. You will need to
contact this person and make sense they have a key listed.
Then you can resend the message.
EOF10
  end
end

class RevokedKey < GPGError
  def initialize(key)
      @message = <<EOF11
En/decryption could not occur because a public key for
   
   #{key}

Has been revoked by its owner. You will need to
contact this person and ask them to upload a new key.
Then you can resend the message.
EOF11
  end
end

class ExpiredKey < GPGError
  def initialize(key)
    @message = <<EOF12
En/decryption could not occur because a public key for
   
   #{key}

Has expired. You will need to contact this person and ask then
to upload a new key.
Then you can resend the message.
EOF12
  end
end

class UntrustedKey < GPGError
  def initialize(key)
    @message = <<EOF13
En/decryption could not occur because a public key for
   
   #{key}

Does not have sufficient trust. You will need to
contact this person and then sign their key using
GnuPG, then you can resend the message. 
EOF13
  end
end

class GPGGeneralError < GPGError
  def initialize(status,args)
    @message = <<EOF14
A general GPG error has occurred.
The status log was:

#{status}

The arguments were 

#{args}

Please forward this message to a wegechick developer
EOF14
  end
end

class GPG
  
  Algos = {'1'=>'RSA','2'=>'RSA encrypt', '3'=>'RSA sign',
    '16'=>'Elgamal','17'=>'DSA', '20'=>'old Elgamal'}
  TrustLevel = {'o'=>'Unknown', 'e'=>'Expired', 'n'=>'No trust', 
    '-'=>'Untrusted', 'q'=>'Untrusted', 'm'=>'Marginal trust',
    'f'=>'Fully trusted', 'u'=>'Ultimately trusted', 'd'=>'Disabled', 
    'i'=>'Invalid', 'r'=>'Revoked'}
  
  def initialize(gpg_exe=nil)
    @gpg = gpg_exe
    unless @gpg
      ["C:\\Program Files\\GNU\\GnuPG\\gpg.exe","C:\\Program Files\\Wedgechick\\gpg.exe","/usr/bin/gpg"].each do |f|
        @gpg = f if File.executable? f
      end
    end
  end
  
  def run (args, textin=nil,give_me_status=false)
    mode = "w"
    r = nil
    gpg_failed = false
    status = tempfile("_rUn") do |tf|
      a = @gpg + " --status-file #{tf} --auto-key-locate #{$cfg['keyserver']} "
      if not textin
        a = a + "--batch --no-tty --yes "
        mode = "r"
      end
      a = a + args
      begin 
        r = IO.popen(a,mode) do |io|
          if textin
            io.write textin
            nil
          else
            io.read
          end
        end
      rescue
        # usually a pipe error
        gpg_failed = true
      end
    end
    print status
    if status =~ /INV_RECP 0 (.*)/ or status =~ /INV_RECP 1 (.*)/
      raise NoPubKey.new($1)
    end
    if status =~ /INV_RECP 4 (.*)/
      raise RevokedKey.new($1)
    end
    if status =~ /INV_RECP 5 (.*)/
      raise ExpiredKey.new($1)
    end
    if status =~ /INV_RECP 10 (.*)/
      raise UntrustedKey.new($1)
    end
    if status =~ /NO_SECKEY /
      raise WrongKey.new
    end
    if gpg_failed
      raise GPGGeneralError.new(status,args)
    end
    r = status if give_me_status
    return r
  end
  
  def tempfile(nesting="")
    fname = Dir.tmpdir + File::Separator + 't' + $$.to_s + nesting+ '.txt'
    begin
      yield fname
      io = File.new(fname,"r")
      t = io.read
      io.close
    ensure
      File.unlink fname if File.exists? fname
    end
    return t
  end
  
  def list_keys (key="",type="keys")
    d = run("--with-colons --list-#{type} #{key} --with-fingerprint")
    return parse_keylist(d)
  end
  
  def list_sigs (key="")
    list_keys(key,"sigs")
  end
  
  def list_secret_keys (key="")
    list_keys(key,"secret-keys")
  end
  
  def parse_keylist (text)
    keys = []
    text.each do |line|
      line = line.strip.split(':')
      if line[0] == 'pub' or line[0] == 'sec'
        keys << {:trust=>TrustLevel[line[1]], :length=>line[2], :algorithm=>GPG::Algos[line[3]],
          :key_id=>line[4],:creation=>line[5], :expires=>line[6],
          :ownertrust=>line[8], :user_id=>[line[9]], :capabilities=>line[11]}
      elsif line[0] == 'fpr'
        keys[-1][:fingerprint] = line[9]
      elsif line[0] == 'uid'
        keys[-1][:user_id] << line[9]
      elsif line[0] == 'sig':
          keys[-1][:signatures] = [] if not keys[-1].has_key? :signature
        keys[-1][:signatures] << {:algorithm=>GPG::Algos[line[3]], :creation=>line[5],
          :user_id=>line[9], :key_id=>line[4]}
      end
    end
    return keys
  end
  
  def gen_key(real, comment, email, length='1024', expiry='5y')
    key_request = """Key-Type: 17
Key-Length: %s
Key-Usage: sign
Subkey-Type: 16
Subkey-Length: %s
Subkey-Usage: encrypt
Name-Real: %s
Name-Email: %s
Name-Comment: %s
Expire-Date: %s
%%commit
""" % [length, length, real, email, comment, expiry]
    return parse_key_gen(run("--batch --gen-key ",key_request,true))
  end
  
  def parse_key_gen (gpg)
    raise GPGError.new(1001),"Error in key generation" unless /KEY_CREATED (B|P) ([0-9A-F]+)/ =~ gpg
    return $+
  end
  
  def import_keys (key_data)
    run("--import", key_data)
  end
  
  def export_keys (key)
    run ("--armor --export #{key}")
  end
  
  
  def sign_key (key)
    return run("--sign-key #{key}","Y\r\n")
  end
  
  def decrypt(crypttext)
    tempfile { |tf| run("--decrypt -o %s" % [tf],crypttext)}
  end
  
  def verify(signed,signature)
    temp1 = Dir.tmpdir + File::Separator + 'xx' + $$.to_s + '.txt'
    h = {}
    status = ""
    begin
      f = File.new(temp1,'w')
      f.write signature
      f.close
      status = run("--verify %s -" % temp1,signed,true)
    ensure
      h = parse_status(status)
      h[:plaintext] = signed
      File.unlink(temp1) if File.writeable? temp1
    end
    return h
  end
  
  def decrypt_verify (crypttext)
    temp1 = Dir.tmpdir + File::Separator + 't' + $$.to_s + '.txt'
    statustext = ""
    plaintext = ""
    begin
      statustext = run("--decrypt -o %s" % temp1,crypttext,true)
    ensure
      plaintext = IO.open(temp1,"r") {|f| f.read} if File.readable? temp1
      File.unlink(temp1) if File.exists? temp1
      h = parse_status(statustext)
    end
    h[:plaintext] = plaintext
    return h
  end

  
  def sign(plaintext)
    tempfile {|tf| run("--armor -o #{tf} --detach-sign",plaintext) }
  end
  
  def delete_secret_key (key)
    d = run("") # FIXME: what's the command here?
  end 
  
  def parse_status (gpg)
    result = {}
    if /GOODSIG ([0-9A-F]+) (.*)/ =~ gpg
      result[:key_id] = $1
      result[:user_id] = $2
    end
    if /ERRSIG +([0-9A-F]+) +[^ ]+ +[^ ]+ +[0-9A-F][0-9A-F] +([0-9]+)/ =~ gpg
      if $2 == '9'
        raise NoPubKey.new($1)
      else
        raise GPGGeneralError.new(gpg,"unknown")
      end
    end
    if /VALIDSIG ([0-9A-F]+) (\S+)/ =~ gpg
      result[:signature] = $1
      result[:creation] = $2
    elsif result[:key_id] # if we have a key but it's not valid
      raise UntrustedKey.new(result[:user_id])
    end
    return result
  end
  
  def search_keys (query,keyserver)
    d = run("--with-colons --keyserver #{keyserver} --search #{query}")
    return parse_searchlist(d)
  end
  
  
  def parse_searchlist (text)
    keys = []
    text.each do |line|
      line = line.strip.split(':')
      if line[0] == 'pub'
        keys << {:length=>line[3], :algorithm=>GPG::Algos[line[2]],
            :key_id=>line[1],:creation=>DateTime.strptime(line[4],"%s").strftime("%Y-%m-%d"),:user_id=>[]}
      elsif line[0] == 'uid'
          keys[-1][:user_id] << line[1]
      end
    end
    return keys
  end
  
  def send_key(key,keyserver)
    run("--keyserver #{keyserver} --send-keys #{key}")
  end
  
  def recv_key(key,keyserver)
    run("--keyserver #{keyserver} --recv-keys #{key}")
  end
  
  def refresh(keyserver)
    run("--keyserver #{keyserver} --refresh-keys")
  end
  
  
  def encrypt (plaintext, recipient)
    tempfile {|tf| run("--batch --no-tty --armor -o #{tf} -r #{recipient} --encrypt", plaintext)}
  end
  
  def encrypt_sign(plaintext,recipient)
    tempfile {|tf| run("--batch --no-tty --armor -o #{tf} -r #{recipient} --sign --encrypt", plaintext)}
  end
  
  def sign(plaintext)
    tempfile {|tf| run("--armor -o #{tf} --detach-sign",plaintext) }
  end
  
  def delete_secret_key (key)
    d = run("") # FIXME: what's the command here?
  end 
  
  def parse_status (gpg)
    result = {}
    if /GOODSIG ([0-9A-F]+) (.*)/ =~ gpg
      result[:key_id] = $1
      result[:user_id] = $2
    end
    if /ERRSIG +([0-9A-F]+) +[^ ]+ +[^ ]+ +[0-9A-F][0-9A-F] +([0-9]+)/ =~ gpg
      raise NoPubKey($1) if $2 == '9'	
    end
    if /VALIDSIG ([0-9A-F]+) (\S+)/ =~ gpg
      result[:signature] = $1
      result[:creation] = $2
    elsif result[:key_id] # if we have a key but it's not valid
      raise UntrustedKey(result[:key_id])
    end
    return result
  end
  
  def search_keys (query,keyserver)
    d = run("--with-colons --keyserver #{keyserver} --search #{query}")
    return parse_searchlist(d)
  end
  
  
  def parse_searchlist (text)
    keys = []
    text.each do |line|
      line = line.strip.split(':')
      if line[0] == 'pub'
        keys << {:length=>line[3], :algorithm=>GPG::Algos[line[2]],
          :key_id=>line[1],:creation=>DateTime.strptime(line[4],"%s").strftime("%Y-%m-%d"),:user_id=>[]}
      elsif line[0] == 'uid'
        keys[-1][:user_id] << line[1]
      end
    end
    return keys
  end
  
  def send_key(key,keyserver)
    run("--keyserver #{keyserver} --send-keys #{key}")
  end
  
  def recv_key(key,keyserver)
    run("--keyserver #{keyserver} --recv-keys #{key}")
  end
  
  def refresh(keyserver)
    run("--keyserver #{keyserver} --refresh-keys")
  end
  
  def adduid(real,comment,email)
    key = list_secret_keys[0][:key_id]
    run("--command-fd 0 --edit-key #{key} adduid","%s\n%s\n%s\nquit\ny\n" % [real,email,comment])
  end
end

def gpg_test
  gpg = GPG.new
  gpg.search_keys("Ian Haywood","wwwkeys.pgp.net")
end
