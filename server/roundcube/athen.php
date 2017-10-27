<?php

/*
** Plugin athen for RoundcubeMail
**
** Description: Medical-specifc headers for Roundcube when running on an ATHEN server
**
** @version 1.0
** @license GPL
** @author Ian Haywood
** @url http://github.com/ihaywood3/athen
** based on the Custom-From plugin by Remi Caput, from https://github.com/r3c/Custom-From
*/

class	athen extends rcube_plugin
{


  /*
  ** Initialize plugin.
  */
  public function init ()
  {
    $this->add_hook ('render_page', array($this, 'render_page'));
    $this->add_hook ('storage_init', array($this, 'storage_init'));
    $this->add_hook('message_headers_output', array($this, 'message_headers'));
    $this->register_action('plugin.view_log', array($this, 'view_log'));
    $this->register_handler('plugin.body', array($this, 'view_log_generate_html'));
  }
  
  
  public function storage_init($p)
  {
    $p['fetch_headers'] = trim($p['fetch_headers'] . ' ' . ' ' . strtoupper('X-OpenPGP-Status'));
    return $p;
  }
  
  public function message_headers($p)
  {
    /* We only have to check the headers once and this method is executed more than once,
       /* so let's cache the result */
    
    if (!$this->message_headers_done) {
      $this->message_headers_done = true;
      $this->log_link = $this->create_log_link($p['headers']);
    } 
    
    $p['output']['log'] = array(
				'title' => 'Status',
				'html' => true,
				'value' => $this->log_link
				);
    return $p;
  }
  
  public function create_log_link($headers)
  {
    if (! $headers->messageID) { return "No message ID"; }
    $db = $this->get_db();
    if (! $db) { return "No log database"; }
    $res = $db->query("select status, rowid from messages where message_id = '" . SQLite3::escapeString($headers->messageID) . "'");
    $row = $res->fetchArray();
    $db->close();
    if ( ! ($row && $row['status']) ) { return "No status found"; }
    $spanclass = "error";
    if ($row['status'] == "OK") $spanclass = "ok";
    if ($row['status'] == "PENDING") $spanclass = "pending";
    return "<span class=\"" . $spanclass . "\">" . $row['status'] . "</span>&nbsp;<a title=\"View message audit log\" href=\"#\" onclick=\"return rcmail.command('plugin.view_log','" 
      . rcmail::JQ($row['rowid']) . "',this,event)\">Audit Log</a>";
  }
  

  private function get_unix_username()
  {

    $rc = rcmail::get_instance();
    $username = $rc->get_user_name();
    // its unclear from code whether we get just the UNIX username or username@domain
    list($local, $domain) = explode('@', $username);
    return $local;

  }

  private function get_db()
  {
    $dbpath = "/home/athen/home/" . $this->get_unix_username() . "/data.sqlite";
    if (is_readable($dbpath))
      {
	return new SQLite3($dbpath, SQLITE3_OPEN_READONLY);
      } else {
	return null;
      }
  }

  public function view_log()
  {
    $rc = rcmail::get_instance();
    rcube::console("view_log _GET: " . print_r($_GET,true));
    $this->msgid = $_GET['_msgid'];
    $this->debug = $_GET['_debug'] == "1";
    $rc->output->set_pagetitle('Message Audit Log');
    $rc->output->send('plugin');
  }

  public function view_log_generate_html()
  {
    $LEVELS = array(0 => "debug", 1=>"normal", 2=>"error");
    $db = $this->get_db();
    $table = new html_table(array("class"=>"log","cols"=>($this->debug ? 3 : 2)));
    $res = $db->query("select strftime('%Y-%m-%dT%H:%M:%SZ',logtime) as time, logtext, extra, level from log where messages_rowid = " . SQLite3::escapeString($this->msgid). " order by logtime");
    while ($row = $res->fetchArray())
      {
	rcube::console("view_log_generate_html row: " . print_r($row,true));
	if ($this->debug || $row['level'] >= 1)
	  {
	    $table->add_row(array('class'=>$LEVELS[$row['level']]));
	    $table->add(array('class'=>"logtime"),$row['time']);
	    $table->add(array(),Q($row['logtext']));
	    if ($this->debug)
	      $table->add(array(),Q($row['extra']));
	  }
      }
    $db->close();
    return "<h1>Audit Log</h1> \n" . $table->show();
  }

  public function render_page ($params)
  {
    rcube::console("render_page params['template']: " . print_r($params['template'],true));
    if ($params['template'] == 'compose')
      {
	$this->include_script ('athen.js');
      }

    if ($params['template'] == 'message')
      {
	$this->include_script ('viewlog.js');
	$this->include_stylesheet("viewlog.css");
      }
    if ($params['template'] == 'plugin')
      {
	$this->include_script('plugin.js');
	$this->include_stylesheet("viewlog.css");
      }
    return $params;
  }
}
  
  ?>
