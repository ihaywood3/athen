<html>
<head>
<title>List Of Users</title></head>
<body>
<table>
<tr><th>username</th><th>Real Name</th><th>Telephone</th><th>Profession</th><th>Provider Number</th><th>Organisation</th><th>Town</th><th>State</th><th>Status</th></tr>
<?php
$db = SQLite3("/data/users.db",SQLITE3_OPEN_READWRITE);
$result = $db->query("select * from account");
while ($row = $result->fetchArray())
    {
		?>
<tr><td><?= htmlspecialchars($row['username']) ?></td>
<td><?= htmlspecialchars($row['realname']) ?></td>
<td><?= htmlspecialchars($row['telephone']) ?></td>
<td><?= htmlspecialchars($row['profession']) ?></td>
<td><?= htmlspecialchars($row['provider']) ?></td>
<td><?= htmlspecialchars($row['organisation']) ?></td>
<td><?= htmlspecialchars($row['town']) ?></td>
<td><?= htmlspecialchars($row['state']) ?></td>
<td><?= htmlspecialchars($row['status']) ?></td>
<td><a href="/edit_user.php?login=<?= $username ?>&mode=edit">Edit</a></td>
</tr>
</php
	} // if
} // while
$db->close();
?>
</table><p/>
<a href="/edit_user.php?mode=new">New User</a></body></html>
