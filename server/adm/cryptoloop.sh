
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
    NUID=$(stat -c '%u' /home/athen/home/$USER)
    HOME=/home/athen/home/$USER chpst -u :$NUID:2000 $GPGSCRIPT kill_agent
    scan_loop $USER
    log "unmounting $USER ( $LOOPDEV )"
    umount /dev/mapper/$USER
    cryptsetup close $USER
    losetup -d $LOOPDEV
}

function resize_home () {
    # assume mounted already
    USER=$1
    EXTRA=$2 # to add, in k

    LOOPDEV=`losetup | awk -v u=/home/athen/home/$USER.img '$6==u {print $1}'`
    umount /dev/mapper/$USER
    dd if=/dev/urandom bs=1024 count=$EXTRA >> /home/athen/home/$USER.img # add random data
    losetup -c $LOOPDEV
    cryptsetup resize /dev/mapper/$USER
    e2fsck -fp /dev/mapper/$USER
    resize2fs /dev/mapper/$USER
    mount /dev/mapper/$USER /home/athen/home/$USER

}

function resize_home_if_required () {
    # assume mounted already
    USER=$1
    # the total in the user's spool
    # yes it's encrypted but we can assume final size will be no more than double what's pending
    spool_size $USER
    AVAIL=`df | awk -v u=/dev/mapper/$USER '$1==u {print $4}'`
    IMAGESIZE=`stat -c '%s' /home/athen/home/$USER.img`
    let "IMAGESIZE=IMAGESIZE >> 10" # stat uses bytes, so convert to k 
    let "EXTRA=51200-AVAIL+(SPOOLSIZE*2)"
    if (( EXTRA > 0 )) ; then 
	if (( IMAGESIZE+EXTRA > 512000 )) ; then
	    log "WARNING user $USER:  going above 500 meg"
	fi
	if (( IMAGESIZE+EXTRA > 614400 )) ; then
	    log "WARNING user $USER: I refuse to go above 600 meg"
	    let "EXTRA=614400-IMAGESIZE"
	fi
	if (( EXTRA > 0 )) ; then
	    resize_home $USER $EXTRA
	fi
    fi
}
