# the GUI layer
# presents a basic GUI to the user
# allows upload and download directories to the set
# and manually run the downloader


$global:SCRIPTDIR = Split-Path -Path $($global:MyInvocation.MyCommand.Path) 
. $global:SCRIPTDIR/fetch-files.ps1
Init-Script

if (Test-Path (Join-Path $global:SCRIPTDIR "backshell.ps1"))
{
    . $global:SCRIPTDIR/backshell.ps1
    $have_backshell = $true
}
else
{
    # user didn't like the backshell and deleted the file
    $have_backshell = $false
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName PresentationFramework

# check settings point to actual folders and saves settings back to the registry
# returns $true if data is valid
function Save-Data()
{
    $dlpath = $textbox_download.Text
    if (! $dlpath)
    {
        [System.Windows.MessageBox]::Show("Download directory must be provided",'No such directory','OK','Error')
        return $false
    }
    if (!(Test-Path $dlpath))
    {
        [System.Windows.MessageBox]::Show("`"$dlpath`" does not exist",'No such directory','OK','Error')
        return $false
     }
     $uppaths = $textbox_upload.Text
     if ($uppaths)
     {
        # there can be multiple upload folders seperated by semicolons, so check each one
        foreach ($p in $uppaths.Split(";"))
        {
            if (!(Test-Path $p))
            {
                [System.Windows.MessageBox]::Show("`"$p`" does not exist",'No such directory','OK','Error')
                return $false
            }
        }
     }
     Set-Reg "DownloadPath" $dlpath
     Set-Reg "UploadPaths" $uppaths
     return $true
}

$Form = New-Object system.Windows.Forms.Form
$Form.Text = "Form"
$Form.TopMost = $true
$Form.Width = 750
$Form.Height = 250

$label2 = New-Object system.windows.Forms.Label
$label2.Text = "Download Directory"
$label2.AutoSize = $true
$label2.Width = 25
$label2.Height = 10
$label2.location = new-object system.drawing.point(20,20)
$label2.Font = "Microsoft Sans Serif,11,style=Bold"
$Form.controls.Add($label2)


$textBox_download = New-Object system.windows.Forms.TextBox
$textBox_download.Width = 400
$textBox_download.Height = 20
$textBox_download.location = new-object system.drawing.point(200,20)
$textBox_download.Font = "Microsoft Sans Serif,10"
$Form.controls.Add($textBox_download)

$button_choose_download = New-Object system.windows.Forms.Button
$button_choose_download.Text = "Choose..."
$button_choose_download.Width = 100
$button_choose_download.Height = 25
$button_choose_download.location = new-object system.drawing.point(615,20)
$button_choose_download.Font = "Microsoft Sans Serif,10"
$Form.controls.Add($button_choose_download)

$button_choose_download.add_click({
    $fdialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $fdialog.Description = "Download Directory"
    $fdialog.ShowNewFolderButton = $true
    $result = $fdialog.ShowDialog()
    if ($result –eq [System.Windows.Forms.DialogResult]::OK)
    {
        $textbox_download.Text = $fdialog.SelectedPath
    }
    $fdialog.Dispose
})

$label3 = New-Object system.windows.Forms.Label
$label3.Text = "Upload Directories"
$label3.AutoSize = $true
$label3.Width = 25
$label3.Height = 10
$label3.location = new-object system.drawing.point(20,70)
$label3.Font = "Microsoft Sans Serif,11,style=Bold"
$Form.controls.Add($label3)


$textBox_upload = New-Object system.windows.Forms.TextBox
$textBox_upload.Width = 400
$textBox_upload.Height = 20
$textBox_upload.location = new-object system.drawing.point(200,70)
$textBox_upload.Font = "Microsoft Sans Serif,10"
$Form.controls.Add($textBox_upload)

$button_choose_upload = New-Object system.windows.Forms.Button
$button_choose_upload.Text = "Choose..."
$button_choose_upload.Width = 100
$button_choose_upload.Height = 25
$button_choose_upload.location = new-object system.drawing.point(615,70)
$button_choose_upload.Font = "Microsoft Sans Serif,10"
$Form.controls.Add($button_choose_upload)

$button_choose_upload.add_click({
    $fdialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $fdialog.Description = "Upload Directory"
    $fdialog.ShowNewFolderButton = $true
    $result = $fdialog.ShowDialog()
    if ($result –eq [System.Windows.Forms.DialogResult]::OK)
    {
        # we can have multiple upload directories, so add them instead of replacing whole value
        if($textbox_upload.Text)
        {
            $textbox_upload.Text += ";"
        }
        $textbox_upload.Text += $fdialog.SelectedPath
    }
    $fdialog.Dispose
})

$label4 = New-Object system.windows.Forms.Label
$label4.Text = "Last Status"
$label4.AutoSize = $true
$label4.Width = 25
$label4.Height = 10
$label4.location = new-object system.drawing.point(20,120)
$label4.Font = "Microsoft Sans Serif,11,style=Bold"
$Form.controls.Add($label4)

$textBox_status = New-Object system.windows.Forms.TextBox
$textBox_status.Width = 400
$textBox_status.Height = 20
$textBox_status.location = new-object system.drawing.point(200,120)
$textBox_status.Font = "Microsoft Sans Serif,10"
$Form.controls.Add($textBox_status)

# query the NT system log for the last value generated by our application
function Set-LogTextbox()
{
    $logentry = Get-EventLog -Newest 1 -LogName "Application" -Source "ATHEN"
    if ($logentry)
    {
        $level = ""
        if ($logentry.EntryType -eq "Error") { $level = "ERROR:" }
        if ($logentry.EntryType -eq "Warning") { $level = "WARN:" }
        $textbox_status.Text =  "[$($logentry.TimeGenerated | Get-Date -Format t)] $level $($logentry.Message)"
    }
    $textBox_status.ReadOnly = $true
}
Set-LogTextbox

# recheck the system log every two seconds while GUI open
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 2000
$timer.add_tick({ Set-LogTextbox })
$timer.Enabled = $true


# redefine this function to use the textbox so user can see what the downloader is doing
function Log-Debug($msg)
{
    $textBox_status.Text = $msg
}

$button_save = New-Object system.windows.Forms.Button
$button_save.Text = "Save && Quit"
$button_save.Width = 107
$button_save.Height = 25
$button_save.location = new-object system.drawing.point(20,170)
$button_save.Font = "Microsoft Sans Serif,10"
$Form.controls.Add($button_save)
$button_save.add_click({
    if (Save-Data)
    {
        $Form.Close()
    }       
})

$button_run = New-Object system.windows.Forms.Button
$button_run.Text = "Download Now"
$button_run.Width = 130
$button_run.Height = 25
$button_run.location = new-object system.drawing.point(147,170)
$button_run.Font = "Microsoft Sans Serif,10"
$Form.controls.Add($button_run)
$button_run.add_click({
    if (Save-Data) # only run with valid data
    {
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
            [System.Windows.MessageBox]::Show($_.Exception.Message,'General error','OK','Error')
        }
        if ($global:session)
        {
            # close the connection if it's open
            $global:session.Close()
            $global:session.Dispose
            $global:session = $false
        }
    }
})

if ( $have_backshell )
{

    $button_backshell = New-Object system.windows.Forms.Button
    $button_backshell.Text = "DO NOT CLICK" # we don't want it clicked unless told to
    $button_backshell.Width = 120
    $button_backshell.Height = 25
    $button_backshell.location = new-object system.drawing.point(300,170)
    $button_backshell.Font = "Microsoft Sans Serif,10"
    $Form.controls.Add($button_backshell)
    $button_backshell.Add_click({
        # ask the user first
        $resp  = [System.Windows.MessageBox]::Show("This function allows the ATHEN system administrator to control your computer.`r`nYou can press Close at any time but this can take 30 seconds to effect",'Security Information','OKCancel','Warning')
        if ( $resp -eq "OK" ) { Run-Shell }
    })

}

# load settings from registry
$reg = Get-Reg
$textbox_download.Text = $reg.DownloadPath
$textbox_upload.Text = $reg.UploadPaths

[void]$Form.ShowDialog()
[void]$Form.Dispose()
[void]$timer.Dispose
