Custom-From README file
=======================

Overview
--------

This plugin adds special features for ATHEN to Roundcube


Install
-------


apt-get install roundcube roundcube-sqlite3 roundcube-plugins apache2
a2enmod ssl
a2ensite default-ssl

move into /etc/roundcube/plugins/athen

sudo php5enmod mcrypt

Then add a reference to this plugin in RoundCube plugins list located in
`<RoundCube install folder>config/main.inc.php` configuration file (update the
`$config['plugins']` variable). Ensure your web user has read access to the
plugin directory and all files in it.

Usage
-----

Once plugin is installed, custom sender button will appear at the right
hand side of the identity selection list.

If you want to disable the "automatic replacement on reply" feature, rename
`config.inc.php.dist` file into `config.inc.php`, uncomment the line with a
parameter named `custom_from_compose_auto` and set this value to `false`.

Thanks
------

- dwurf (https://github.com/dwurf) for the globals $IMAP and $USER fix
- Peter Dey (https://github.com/peterdey) for the custom header feature
- kermit-the-frog (https://github.com/kermit-the-frog) for various bugfixes
