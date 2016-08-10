
function scan_loop()
{
   LOOPDEV=`losetup -a | awk -F '[:() ]+' -v u=/home/athen/home/$1.img '$4==u {print $1; nextfile}'`
}

# mount a given user's home directory
# params: USERNAME PASSWORD
function mount_home() {

    USER=$1
    PASSWD=$2
    log "mounting home for USER=$USER"
    losetup -f /home/athen/home/$USER.img
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



function umount_home() {   
    USER=$1
    scan_loop $USER
    log "unmounting $USER ( $LOOPDEV )"
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
