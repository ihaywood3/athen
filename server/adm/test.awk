  FILENAME == "ps" &&  $11 == "dovecot/imap" {online["/dev/mapper/" $1]=1 } 
  FILENAME == "mounts" && !($1 in online) && substr($3,0,11) == "/home/athen" {print substr($1,13)}
END {
	for (i in online)
		print i, online[i];
}
