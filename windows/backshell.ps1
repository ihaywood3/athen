# backshell.ps1
# .SYNOPSIS
# a reverse shell for remote maintenance of client machine
# .DESCRIPTION
# provides a powershell access on the client machine to the server via the ssh
# inefficient method due to WinSCP limitations
# its a massive security hole: hence only runs under direct user supervision, and
# all entered commands displayed on the textbox
# if you are still nervous you can delete or not install this file
# the rest of the downloader client will run



function Prompt()
{
    Return "PS $(pwd) > "
}

function Run-Shell()
{
    $script:closeflag = $false
    
    $Form = New-Object system.Windows.Forms.Form
    $Form.Text = "Remote Help"
    $Form.TopMost = $true
    $Form.Width = 447
    $Form.Height = 148


    $script:textBox = New-Object system.windows.Forms.TextBox
    $script:textBox.Width = 393
    $script:textBox.Height = 20
    $script:textBox.location = new-object system.drawing.point(19,18)
    $script:textBox.Font = "Microsoft Sans Serif,10"
    $script:textBox.ReadOnly = $true
    $Form.controls.Add($script:textBox)


    $button_close = New-Object system.windows.Forms.Button
    $button_close.Text = "Close"
    $button_close.Width = 60
    $button_close.Height = 30
    $button_close.location = new-object system.drawing.point(187,57)
    $button_close.Font = "Microsoft Sans Serif,10"
    $Form.controls.Add($button_close)
    $button_close.Add_click({
         $Form.Close()
        $script:closeflag = $true
    })
    $Form.Add_FormClosing({ $script:closeflag = $true })
    [void]$Form.Show()

    # get the current user name (on the server, what we use to log in)
    $uname = (Get-Reg).username
    $session = Login-Server
    $flag = $true
    # greeting for the terminal on the server
    $outdata = "Windows PowerShell on "+( [System.Environment]::MachineName)+"`r`n"+(Prompt)
    while ($flag)
    {
        $cmd = ""
        if ($outdata)
        {
            if($outdata.Length -gt 8196) 
            # apparently Linux can handle up to 2 meg on the command line
            # but the WinSCP library chokes on anything longer than 10k
            {
                # so big responses go the slow way with temorary files
                $tempFile = [io.path]::GetTempFileName()
                $outdata >> $tempFile
                $transferOptions = New-Object WinSCP.TransferOptions
                $transferOptions.TransferMode = [WinSCP.TransferMode]::Binary
 
                $transferResult =
                $session.PutFiles($tempFile, "/tmp/$uname.inputdata", $False, $transferOptions)
                $transferResult.Check()
            
                $cmd = "cat /tmp/$uname.inputdata > /var/run/athen/$uname.input ; rm /tmp/$uname.inputdata ; "
                Remove-Item $tempFile
            }
            else
            {
                # short responses get escaped and fed in on the command line, this reduces roundtrip delay.
                $cmd = "echo -n '"+(Shell-Escape $outdata)+"' > /var/run/athen/$uname.input ; "
            }
        }
        # wait for the next command
        $cmd += "timeout 30s cat /var/run/athen/$uname.output"
        $resp = $session.ExecuteCommand($cmd)
        $resp = $resp.Output
        if ($resp)
        {
            $resp = $resp.Trim()
            $script:textBox.Text = $resp
        }
        # let the command be displayed, and check if user has pressed "Close" button
        [System.Windows.Forms.Application]::DoEvents()
        if ($script:closeflag)
        {
            # user at this end pressed Closed
            $flag = $false
            # tell the remote user
            $dum = $session.ExecuteCommand("timeout 2s echo 'local user has closed shell' > /var/run/$uname.input")
        }
        elseif ($resp)
        {
            if ($resp -eq "quit")
            {
                # remote user wants to close down
                $flag = $false
                $Form.Close()
            }
            else
            {
                try
                {
                    # run the entered command in local PowerShell context
                    $outdata=(Invoke-Expression $resp | Out-String)
                }
                catch [Exception]
                {
                    # report errors back to the remote user
                    $outdata=$_.Exception.Message
                }
                $outdata += (Prompt)
            }
        }
        else
        {
            $outdata = ""
        }
    }
    # close the session
    [void]$session.Close()
    [void]$session.Dispose()
    [System.Windows.Forms.Application]::DoEvents()
    [void]$Form.Dispose
}
