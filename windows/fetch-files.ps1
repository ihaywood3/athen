function Login-Server()
{
    $reg = Get-Reg
    if (! $reg.host)
    {
        throw "No registry keys for login"
    }
    $sessionOptions = New-Object WinSCP.SessionOptions -Property @{
        Protocol = [WinSCP.Protocol]::Sftp
        # the hostname of the server to connect to
        HostName = $reg.host # "10.0.2.2"
        # use Session.ScanFingerprint() to get this value       
        SshHostKeyFingerprint = $reg.fingerprint # "ssh-ed25519 256 fe:5c:ab:55:8a:27:aa:03:1b:05:fb:a7:ca:38:20:67"
        #  the username to connect to
        UserName = $reg.username
        # the password 
        Password = $reg.password
    }
    try 
    {
        $global:session = New-Object WinSCP.Session
        $global:session.Open($sessionOptions)
        return $global:session
    }
    finally
    {
        $global:session = $false
    } 
}

function Init-Script() 
{

   $global:session = $false
   $global:loggerbox = $false
   $global:registryPath = "HKCU:\Software\ATHEN\Settings"
    # each calling script has to so this
   #$global:SCRIPTDIR = Split-Path -Path $($global:MyInvocation.MyCommand.Path) 
   Add-Type -Path (Join-Path $global:SCRIPTDIR "WinSCPnet.dll")
 
}

function Init-System()
{
    # create registry key if not exists
    If(!(Test-Path $global:registryPath))
    {
        # this is a bit of a furphy because in reality the installer
        # will have set up the registry for us
        New-Item -Path $global:registryPath -Force | Out-Null
    }
    # register us with the NT syslog
    New-EventLog -LogName "Application" -Source "ATHEN"
    # now do some searching for download directories
    If (Test-Path "C:\Zedmed\download")
    {
        Set-Reg "DownloadPath" "C:\Zedmed\download"
    }
    if (Test-Path "C:\Program Files\Health Communication Network\Messages\In")
    { 
        Set-Reg "DownloadPath" "C:\Program Files\Health Communication Network\Messages\In"
    }
    if (Test-Path "C:\Results") # likely Best Practice
    {
       if (!(Test-Path "C:\Results\ATHEN"))
       {
            New-Item "C:\Results\ATHEN" -ItemType directory
       }
       Set-Reg "DownloadPath" "C:\Results\ATHEN"
   }  
}

function Log-Debug($msg)
{
      # no-op unless developing
      Write-Host "$msg"
}

function Log-Info($msg)
{
    Log-Debug "INFO: $msg"
    Write-EventLog -Logname "Application" -Source "ATHEN" -EventID 3001 -EntryType Information -Message "$msg"
    Write-FarLog "INFO" "$msg"
}

function Log-Warning($msg)
{
    Log-Debug "WARNING: "+$msg
    Write-EventLog -Logname "Application" -Source "ATHEN" -EventID 3002 -EntryType Warning -Message "$msg"
    Write-FarLog "WARN" "$msg"
}

function Log-Error($msg)
{
    Log-Debug "ERROR: "+$msg
    Write-EventLog -Logname "Application" -Source "ATHEN" -EventID 3003 -EntryType Error -Message "$msg"
    Write-FarLog "ERR" "$msg"
}

# make a string safe for the shell in single quotes (so only the single quote needs to be escaped)
function Shell-Escape($text)
{
    if ($text)
    {
        $text = $text.Replace("'","'\''")
    }
    return $text
    
}

# the "far log" is the logfile on the athen servwe
function Write-FarLog($level,$msg)
{
    try {
        $level = Shell-Escape $level
        $msg = Shell-Escape $message
        if ($global:session)
        {
            [void] $global:session.ExecuteCommand("echo `date` '$level' '$msg' >> /var/log/athen/remote/$USER.log")
        }
    } catch [Exception]
    {
       # do nothing
    }
}

function Set-Reg($name,$value)
{
    New-ItemProperty -Path $global:registryPath -Name $name -Value $value -PropertyType STRING -Force | Out-Null
}


function Get-Reg()
{
    Return Get-ItemProperty -Path $global:registryPath
}

# get the directory for "mirror" files (empty files of the same name to record what we have downloaded)
function Mirror-Dir()
{
    if (!(Test-Path $env:LOCALAPPDATA)) { New-Item $env:LOCALAPPDATA -Type directory | Out-Null }
    $mirrorDir = (Join-Path $env:LOCALAPPDATA "ATHEN")
    if (!(Test-Path $mirrorDir)) { New-Item $mirrorDir -Type directory | Out-Null }
    $mirrorDir = (Join-Path $mirrorDir "Mirror")
    if (!(Test-Path $mirrorDir)) { New-Item $mirrorDir -Type directory | Out-Null }
    
    return $mirrorDir
}

# parses a tabs-and-newlines style UNIX document into
# a pipeline of Hashtable objects
# $keys - Array of Strings of field names
function Parse-Tabs($output,$keys)
{
    foreach ($line in $output.Split("`n"))
    {
        if ($line)
        {
            [hashtable]$h = @{}
            $i = 0
            foreach ($cell in $line.Split("`t"))
            {
                $h[$keys[$i]] = $cell
                $i++
            }
            Write-Output $h
        }
    }
}

# port of UNIX "touch" (not exact as doesn't set date)
function touch {set-content -Path ($args[0]) -Value ($null)} 


# check an execution result
# if UNIX exit code nonzero throw exception with value of sterr
function Check-Command-Result($response)
{
    $response.Check()
    if ($response.ExitCode -neq 0)
    {
        throw $response.ErrorOutput
    }
}

# download the files
# assume connected $global:session is valid
# exceptions not trapped
function Download-Files
{
    $reg = Get-Reg
    if (!(Test-Path $reg.DownloadPath)) { throw "download path '$($reg.DownloadPath)' not valid" }
    $result = $global:session.ExecuteCommand("/usr/lib/athen/python/list-emails-download.py")
    Check-Command-Result $resp
    
    $transferOptions = New-Object WinSCP.TransferOptions
    $transferOptions.TransferMode = [WinSCP.TransferMode]::Binary
    Parse-Tabs $result.Output "filename","size","message_id" | Foreach-Object {
        $fname = $_.filename
        $message_id = $_.message_id
        Log-Debug "downloading $fname"
        try {
            $dest_file = (Join-Path $reg.DownloadPath $fname)
            $resp2 = $global:session.GetFiles("`$HOME/download/$($_.filename)",$dest_file,$false,$transferOptions)
            $resp2.Check()
            $local_size = (Get-Item $dest_file).Length
            if ([int]$_.size -neq $local_size) { throw "remote size $($_.size) local size $local_size" } 
                        Log-Debug "verified $($_.filename)'"
            Check-Command-Result($global:session.ExecuteCommand("/usr/lib/athen/python/report-file-download.py '$message_id' 'DOWNLOADED'"))
            Set-Content -Path (Join-Path (Mirror-Dir) $fname) -Value $message_id
        } catch [Exception] {
            $errmsg = $_.Exception.Message
            try {
                $errmsg = (Shell-Escape $errmsg)
                Check-Command-Result ($global:session.ExecuteCommand("/usr/lib/athen/python/report-file-download.py '$($_.message_id)' 'ERROR' '$errmsg'"))
            } catch [Exception] {
                # don't try to do anything about errors when reporting errors as this will confuse the issue (which is probably network-related)
                # only the original error is fed back up the stack
            }
            throw "error downloading $fname: $errmsg"
        }
    }
}

# runs through list of downloaded files on the "mirror dir"
# reports back to the server files that are missing
# presumed consumed by the downstream EMR app
# (yes this is a weak way of confirming delivery but best we have)
function Check-Downloaded()
{
    $reg = Get-Reg
    if (!(Test-Path $reg.DownloadPath)) { throw "download path '$($reg.DownloadPath)' not valid" }
    Dir (Mirror-Dir) | Foreach-Object {
        if (!(Test-Path (Join-Path $reg.DownloadPath $_.Name)))
        {
            $message_id = Get-Content $_
            Check-Command-Result ($global:session.ExecuteCommand("/usr/lib/athen/python/report-file-download.py '$message_id' 'DELETED'"))
            Remove-Item $_
            Log-Debug "file '$($_.Name)' reported as processed"
        }
    }
}

function Upload-Files
{
    $reg = Get-Reg
    if ($reg.UploadPaths)
    {
        $transferOptions = New-Object WinSCP.TransferOptions
        $transferOptions.TransferMode = [WinSCP.TransferMode]::Binary
        foreach ($path in $reg.downloadPaths.Split(";"))
        {
            if ($path)
            {
                if (Test-Path $path)
                {
                    Log-Debug "Uploading from '$path'"
                    Dir $path -Recurse | Foreach-Object {
                        if(!($_.PSIsContainer))
                        {
                            Log-Debug "uploading $($_.Name)"
                            $global:session.PutFiles($_.FullName,"`$HOME/upload",False,$transferOptions)
                            Check-Command-Result($global:session.ExecuteCommand("/usr/lib/athen/python/report-file-upload.py '$($_.Name)' $($_.Length)"))
                            Remove-Item $_
                        }
                }
                else
                {
                    Log-Warning "upload '$path' does not exit"
                }
            }    
        }
    }
    else
    {
        Log-Debug "no upload path configured"
    }
}
 