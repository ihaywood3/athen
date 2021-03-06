# this is the script to call from Scheduled Tasks
# does a download without anyy user-interaction: errors are saved to the log

$global:SCRIPTDIR = Split-Path -Path $($global:MyInvocation.MyCommand.Path) 
. $global:SCRIPTDIR/fetch-files.ps1
Init-Script

try
{
   Login-Server
   # do the run
   Download-Files
   Check-Downloaded
   Upload-Files
}
catch [Exception]
{
   Log-Error $_.Exception.Message
}
if ($global:session)
{
   # close the connection if it's open
   $global:session.Close()
   $global:session.Dispose
}