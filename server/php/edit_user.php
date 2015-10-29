<html>
<head>
<title>List Of Users</title></head>
<body>
<table>
<tr><th>username</th><th>Real Name</th><th>Telephone</th><th>Profession</th><th>Provider Number</th><th>Organisation</th><th>Town</th><th>State</th></tr>
<?php

function clean($str)
{
	foreach ($i in array(",",";","/","\\","\n","\r","\t","..",":","\"", "<", ">", "&"))
	{
		$str = str_replace($i," ",$str);
	}
	return $str;
}

$db = SQLite("/data/users.db",SQLITE3_OPEN_READWRITE);
$states = array("New South Wales","Victoria","Tasmania","South Australia","Western Australia","Northern Territory","Queensland","Australian Capital Territory");

$mode = $_REQUEST['mode'];

if ($mode == 'new')
{
	$username = "";
	$realname = "";
	$profession = "";
	$provider_number = "";
	$organisation = "";
	$town = "";
	$state = "";
	$telephone = "";
	$password = "";
	$error = "";
	$confirm = "";
    $status = "P";
}

if ($mode == 'create' || $mode == 'change')
{
	$username = preg_replace("/[^a-z0-9_]+/","",strtolower($_POST['username']));
	$realname = clean($_POST['realname']);
	$profession = preg_replace("/[^a-z \\-]+/","",strtolower($_POST['profession']));
	$provider = preg_replace("/[^0-9A-Z]+/","",strtoupper($_POST['provider']));
	$organisation = clean($_POST['organisation']);
	$town = clean($_POST['town']);
	$state = clean($_POST['state']);
	$telphone = clean($_POST['telephone']);
	$password = $_POST['password'];
	$confirm = $_POST['confirm'];
    $status = $_POST['status'];
	$error = "";
    if (! in_array($status, array("P","A","I")) $error = "Invalid status code";
	if ($username == "") $error = "Must provide username";
	if ($realname == "") $error = "Must provide a real name";
    if ($profession == "") $error = "Must provide a profession";
    if (strlen($realname) > 100) $error = "Real name too long";
    if (strlen($profession) > 50) $error = "Profession is too long";
    if (strlen($username) > 20) $error = "Username is too long";
    if (strlen($organisation) > 100) $error = "Organisation is too long";
    if (strlen($town) > 50) $error = "Town is too long";
    if (! in_array($state,$states)) $error = "State is invalid";
    if (strlen($provider) > 10) $status = "Provider number is too long";
    if (strlen($telephone) > 20) $status = "Telephone is too long";
}

if ($mode == "create")
{
	if ($password == "") $error = "Password cannot be blank";
	if ($password != $confirm) $error = "Password doesn't not match confirmation";
}

if ($mode == "change" && $error == "")
{
	if ($password != "" || $confirm != "")
        {
            $error = "Cannot change password";
        }
    else
        {
            $stmt = $db->prepare("update accounts set realname=:r,profession=:p,organisation=:o,town=:t,state=:s,status=:st,provider=:pr,telephone=:te where username= :u");
            $stmt->bindValue(":u",$username);
            $stmt->bindValue(":r",$realname);
            $stmt->bindValue(":p",$profession);
            $stmt->bindValue(":o",$organisation);
            $stmt->bindValue(":t",$town);
            $stmt->bindValue(":s",$state);
            $stmt->bindValue(":st",$status);
            $stmt->bindValue(":pr",$provider);
            $stmt->bindValue(":te",$telephone);
            $stmt->execute();
            if ($db->changes() == 1)
                {
                    $error = "Successfully changed user";
                }
            else
                {
                    $error = "SQL error:" . $db->lastErrorMsg();
                }
            $stmt->close();
        }
}

if ($mode == "edit" && $error == "")
{
    $stmt = $db->prepare("select * from accounts where username = :u");
    $stmt->bindValue(":u",clean($_GET['username']));
    $result = $stmt->execute();
    if ($row = $result->fetchArray())
        {
            $username = $row['username'];
            $realname = $row['realname'];
            $profession = $row['profession'];
            $provider = $row['provider'];
            $organisation = $row['organisation'];
            $town = $row['town'];
            $state = $row['state'];
            $telphone = $row['telephone'];
            $status = $row['status'];
            $error = "";
            $password = "";
        }
    else
        {
            $error = "Can't find user";
        }
    $stmt->close();
} // if mode == edit


if ($mode == "create" && $error == "")
{
    $stmt = $db->prepare("select * from accounts where username = :u");
    $stmt->bindValue(":u",clean($username));
    $result = $stmt->execute();
    if ($row = $result->fetchArray())
        {
            $stmt->close();
            $error = "Username already exists";
        }
    else
        {
            $stmt->close();
            $stmt = $db->prepare("insert into accounts (username,realname,profession,organisation,town,state,status,provider,telephone) values (:u,:r,:p,:o,:t,:s,:st,:pr,:te)");
            $stmt->bindValue(":u",$username);
            $stmt->bindValue(":r",$realname);
            $stmt->bindValue(":p",$profession);
            $stmt->bindValue(":o",$organisation);
            $stmt->bindValue(":t",$town);
            $stmt->bindValue(":s",$state);
            $stmt->bindValue(":st",$status);
            $stmt->bindValue(":pr",$provider);
            $stmt->bindValue(":te",$telephone);
            $stmt->execute();
            if ($db->changes() == 1)
                {
                    $error = "Successfully created user":
                }
            else
                {
                    $error = "SQL error:" . $db->lastErrorMsg();
                }
            $stmt->close();
        }
    
}

$dest = "change";
if ($mode == "new" || ($mode== "create" && $error != "Successfully created user"))
   $dest = "create";

?>
<html><head><title>
<?php
	if ($mode == "new" && $mode == "create")
	   { echo "New User"; }
	else
	   { echo "Edit User"; }
?></title></head>
<body>
<form method="post" action="/edit_user.php">
<table>
<tr><td>User login:</td><td>
<?php
if ($dest == "create")
    { echo "<input type=\"text\" length="\50\" name=\"username\" value=\"" . $username . "\"/>"; }
    else
    { echo htmlspecialchars($username); }
?></td></tr>
<tr><td>Real Name:</td><td>
<input type="text" name="realname" length="50" value="<?= $realname ?>"/></td></tr>
<tr><td>Profession:</td><td>
<input type="text" name="profession" length="50" id="profession" value="<?= $profession ?>"/></td></tr>
<tr><td>Provider Number:</td><td>
<input type="text" name="provider_number" length="50" value="<?= $provider_number ?>"/></td></tr>
<tr><td>Telephone:</td><td>
<input type="text" name="telephone" length="50" value="<?= $telephone ?>"/></td></tr>
<tr><td>Organisation:</td><td>
<input type="text" name="organisation" length="50" value="<?= $organisation ?>"/></td></tr>
<tr><td>Town:</td><td>
<input type="text" name="town" length="50" value="<?= $town ?>"/></td></tr>
<tr><td>State:</td><td>
<select name="state">
<?php
foreach ($i in $states)
{
	echo "<option";
	if ($i == $state)
	   echo " selected";
	echo ">" . $i;
}
?>
</select>
</td></tr>
<tr><td>Password:</td><td>
<input type="password" name="password" length="50" value="<?= $password ?>"/></td></tr>
<tr><td>Confirm Password:</td><td>
<input name="confirm_password" length="50" /></td></tr>
<tr><td></td><td><input type="submit" /><input type="clear" /></td></tr>
</table>
</form>
<p/>
<a href="/list_users.php">Back to User List</a></body></html>
