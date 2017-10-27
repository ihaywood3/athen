
if (window.rcmail)
{
    rcmail.addEventListener('init', function (event)
			    {
				rcmail.register_command('plugin.view_log', function (props, obj) {
				    rcmail.goto_url("plugin.view_log",{"_msgid":props});
				    }, true);
			    });
}
