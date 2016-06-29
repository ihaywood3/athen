
function scan_loop()
{
   LOOPDEV=`losetup -a | awk -F '[:() ]+' -v u=/home/athen/home/$1.img '$4==u {print $1; nextfile}'`
}

# mount a given user's home directory
# params: USERNAME PASSWORD
function mount_home () {

    USER=$1
    PASSWD=$2
    losetup -f /home/athen/home/$USER.img
    log "trying to mount USER=$USER"
    scan_loop $USER
    log "LOOPDEV=$LOOPDEV"
    if printf "$PASSWD" | cryptsetup open --type luks --key-file=- $LOOPDEV $USER ; then
	log "crypto enabled: about to mount"
	mount /dev/mapper/$USER /home/athen/home/$USER
	log "Directory mounted"
    else
	log "no cryptoloop established: usually wrong password"
	losetup -d $LOOPDEV
	exit 1
    fi
}

# create a new user account and encrypted home directory.
function make_home () {

    USER=$1
    REALNAME=$2
    PASSWD=$3

    if [ ! -e /home/athen/home ] ; then
	mkdir -p /home/athen/home
    fi
    cd /home/athen/home
    if ! grep -q $USER /etc/passwd ; then
	/usr/sbin/useradd -b /home/athen/home -c "$REALNAME,,," -g vmail -M -N $USER
    fi

    if [ ! -e $USER.img ] ; then
	dd if=/dev/zero of=$USER.img bs=1M count=100
	chown $USER:vmail $USER.img
    fi
    if [ ! -e $USER/private.key ] ; then
	losetup -f $USER.img
	scan_loop $USER
	badblocks -s -w -t random -v $LOOPDEV
	printf "$PASSWD" | cryptsetup --force-password luksFormat --key-file=- $LOOPDEV
	printf "$PASSWD" | cryptsetup open --type luks --key-file=- $LOOPDEV $USER
	mkfs.ext4 -j /dev/mapper/$USER
	e2fsck -fp /dev/mapper/$USER
	mkdir $USER
	chown $USER:vmail $USER
	chmod 755 $USER
	mount /dev/mapper/$USER $USER
	mkdir $USER/mail
	chown $USER:vmail $USER/mail
	# make private key and cert in one command
	openssl req -new -x509 -nodes -outform PEM -out $USER.pem -newkey rsa -keyout $USER/private.key -subj "/DC=email/DC=athen/O=$REALNAME" -days 3600 -batch
	chmod 600 $USER/private.key
	chown $USER:vmail $USER/private.key
	sleep 1
	umount /dev/mapper/$USER
	cryptsetup close $USER
	losetup -d $LOOPDEV
    fi
}

function umount_home() {   
    USER=$1
    scan_loop $USER
    umount /dev/mapper/$USER
    cryptsetup close $USER
    losetup -d $LOOPDEV
}

function resize_home () {
    # assume mounted already
    USER=$1
    AVAIL=`df | awk -v u=/dev/mapper/$USER '$1==u {print $4}'`
    if (( AVAIL > 50 )) ; then
	echo More than 50 meg, but resizing anyway
    fi
    LOOPDEV=`losetup | awk -v u=/home/athen/home/$USER.img '$6==u {print $1}'`
    umount /dev/mapper/$USER
    dd if=/dev/urandom bs=1M count=50 >> /home/athen/home/$USER.img # add 50 meg
    losetup -c $LOOPDEV
    cryptsetup resize /dev/mapper/$USER
    e2fsck -fp /dev/mapper/$USER
    resize2fs /dev/mapper/$USER
    mount /dev/mapper/$USER /home/athen/home/$USER
}
