cd `dirname $0`
set -e
. ./cryptoloop.sh

USER=$1
REALNAME=$2
# PASSWD defined in environment

if [ ! -e /home/athen/home ] ; then
    mkdir -p /home/athen/home
fi
cd /home/athen/home
if grep -q $USER /etc/passwd ; then
    echo "ERROR:user already exists in /etc/passwd"
    exit 0
fi

if [ -e $USER.img ] ; then
    echo "ERROR:image file exists /home/athen/home/$USER.img"
    exit 0
fi
echo "PROGRESS:1:creating drive image"
dd status=none if=/dev/zero of=$USER.img bs=4M count=25
echo "PROGRESS:5:adding UNIX user"
/usr/sbin/useradd -b /home/athen/home -c "$REALNAME,,," -g vmail -M -N $USER
chown $USER:vmail $USER.img
echo "PROGRESS:8:set up loopback device"
losetup -f $USER.img
scan_loop $USER
if [ "z$LOOPDEV" == "z" ] ; then
    echo "ERROR:cannot find LOOPDEV"
    exit 0
fi
echo "PROGRESS:9:randomising drive data"
badblocks -w -t random -v $LOOPDEV > /dev/null
echo "PROGRESS:12:encrypting drive"
printf "$PASSWD" | cryptsetup --force-password luksFormat --key-file=- $LOOPDEV
echo "PROGRESS:50:opening encrypted drive"
printf "$PASSWD" | cryptsetup open --type luks --key-file=- $LOOPDEV $USER
unset PASSWD
echo "PROGRESS:65:creating filesystem"
mkfs.ext4 -qj /dev/mapper/$USER 
echo "PROGRESS:67:checking filesystem"
e2fsck -fp /dev/mapper/$USER > /dev/null
echo "PROGRESS:69:creating user directory"
mkdir $USER
chown $USER:vmail $USER
chmod 755 $USER
mount /dev/mapper/$USER $USER
# make private key and cert in one command
echo "PROGRESS:75:generating private key"
openssl req -new -x509 -nodes -outform PEM -out $USER.pem -newkey rsa -keyout $USER/private.key -subj "/DC=email/DC=athen/O=$REALNAME" -days 3600 -batch > /dev/null
echo "PROGRESS:84:creating files"
chmod 600 $USER/private.key
chown $USER:vmail $USER/private.key
mkdir $USER/mail
chown $USER:vmail $USER/mail
echo "PROGRESS:85:unmounting"
sleep 0.3 # make sure above file operations are committed to disc
umount /dev/mapper/$USER
cryptsetup close $USER
losetup -d $LOOPDEV
