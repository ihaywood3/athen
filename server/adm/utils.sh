set +e


date >> /var/log/athen.log
echo Script $0 >> /var/log/athen.log

exec > >(tee "/var/log/athen.log") 2>&1

function password_checksum ()
{
    CHECKSUM=`echo -n $1 | cat $2/salt -`
    COUNTER=0
    while [  $COUNTER -lt 1000 ]; do
        CHECKSUM=`echo -n $CHECKSUM | sha512sum | awk '{print $1}'`
        let COUNTER=COUNTER+1 
    done
    return 0
}
