
if (window.rcmail)
{
    rcmail.addEventListener('init', function (event)
			    {
				$(".logtime").each(function (i) {
				      $(this).text(new Date($(this).text()).toString());
				    });
			    });
}
