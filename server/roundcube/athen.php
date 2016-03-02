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
	public function	init ()
	{
		$this->add_hook ('render_page', array ($this, 'render_page'));;
	}


	public function	render_page ($params)
	{
		if ($params['template'] == 'compose')
		{
			$this->include_script ('athen.js');
		}

		return $params;
	}
}

?>
