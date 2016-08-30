
/*
** Plugin custom_from for RoundcubeMail
**  - Plugin script
*/

var ADDRESS_RE=/\[([A-Za-z\-' ]+), ([A-Za-z\-' ]+) \((M|F)\) DOB: ?([0-9\/]+) (.+), (.+) ([0-9]{4})\] (.*)$/;

function purify(str)
{
    str = str.replace("[","");
    str = str.replace("]","");
    str = str.replace("\n"," ");
    str = str.replace("\r","");
    str = str.replace("(","");
    str = str.replace(")","");
    str = str.replace(","," ");
    str = str.trim();
    return str;
    
    
}

function check_date(str)
{
    var r;
    var day;
    var month;
    var year;
    
    r = str.match(/([0-9]{1,2})\/([0-9]{1,2})\/([0-9]){2,4}/);
    if (! r || r.length< 4) return false;
    day = parseInt(r[1]);
    month = parseInt(r[2]);
    year = parseInt(r[3]);
    if (day < 1 || day > 31) return false;
    if (month < 1 || month > 12) return false;
    if (year < 100) year = year+2000;
    if (year < 1850 || year > 2100) return false;
    return true;
}


if (window.rcmail)
{
    var save_to_subject = function (event)
    {
	var fname = purify($("#patient_firstname").val());
	var sname = purify($("#patient_surname").val());
	var dob = purify($("#patient_dob").val());
	var addr = purify($("#patient_address").val());
	var suburb = purify($("#patient_suburb").val());
	var postcode = purify($("#patient_postcode").val());
	var sex = "M";
	var subj;
	
	if ($("#sex_female").attr("checked")) sex = "F";
	if (fname == "" && sname == "" && dob == "")
	{
	    return true; // no patient data at all
	}
	if (fname == "" || sname == "" || dob == "")
	{
	    alert("Surname, firstname and DOB must be provided if any are provided");
	    return false;
	}
	
	if (! check_date(dob))
	{
	    alert("Birthdate must be in the form dd/mm/yyyy");
	    return false;
	}

	if (postcode != "")
	{
	    var m = postcode.match(/^[0-9]{4}$/);
	    if (! m)
	    {
		alert("Postcode must be 4 digits");
		return false;
	    }
	}
	
	sname = sname.toUpperCase();
	subj = $("#compose-subject").val();
	m = subj.match(ADDRESS_RE);
	if (m)
	    {
		// we need to "gobble up" the existing address data to avoid duplications
		subj = m[7];
	    }
	$("#compose-subject").val( "["+sname+", "+fname+" ("+sex+") DOB:"+dob+" "+addr+", "+suburb+" "+postcode+"] "+subj);
	return true;
	    
    }


    var load_from_subject = function ()
    {	
	var subject;
	var m;

	subject = $("#compose-subject").val();
	if (subject)
	{
	    m = subject.match(ADDRESS_RE);
	    if (m)
	    {
		$("#patient_surname").val(m[1]);
		$("#patient_firstname").val(m[2]);
		if (m[3] == "M")
		{
		    $("#sex_male").attr("checked","checked");
		} else {
		    $("#sex_female").attr("checked","checked");
		}
		$("#patient_dob").val(m[4]);
		$("#patient_address").val(m[5]);
		$("#patient_suburb").val(m[6]);
		$("#patient_postcode").val(m[7]);
		$("#compose-subject").val(m[8]);
	    }
	}
    }
    
    rcmail.addEventListener('beforesavedraft',save_to_subject)
    rcmail.addEventListener('beforesend',save_to_subject)

	rcmail.addEventListener('init', function (event)
				{
				    $("table.compose-headers tr:last").after(
					$("<tr>")
					    .append(
						$("<td>")
						    .addClass("title")
						    .html($("<label>").attr("for", "patient_firstname").html("Patient")),
						$("<td>")
						    .addClass("editfield")
						    .append(
							"Firstname&nbsp;", 
							$("<input>")
							    .attr("id","patient_firstname")
							    .attr("type","text")
							    .attr("name","patient_firstname")
							    .attr("tabindex","9")
							    .attr("style","width: 35%"),
							"&nbsp;Surname&nbsp;",
							$("<input>")
							    .attr("id","patient_surname")
							    .attr("type","text")
							    .attr("tabindex","10")
							    .attr("name","patient_durname")
							    .attr("style","width: 35%")
						    )),
					$('<tr>')
					    .append(
						$("<td>"),
						$("<td>")
						    .addClass("editfield")
						    .append(
							"DOB:&nbsp;",
							$("<input>")
							    .attr("id","patient_dob")
							    .attr("type","text")
							    .attr("tabindex","11")
							    .attr("name","patient_dob")
							    .attr("style","width: 8em"),
							"&nbsp;",
							$("<input>")
							    .attr("id","sex_male")
							    .attr("type","radio")
							    .attr("name","sex")
							    .attr("value","male")
							    .attr("tabindex","12")
							    .attr("style","width: auto"),
							$("<label>").attr("for","sex_male").html("Male&nbsp;"),
							$("<input>")
							    .attr("id","sex_female")
							    .attr("type","radio")
							    .attr("name","sex")
							    .attr("value","female")
							    .attr("tabindex","13")
							    .attr("style","width: auto"),			
							$("<label>").attr("for","sex_female").html("Female"))),
					$('<tr>')
					    .append(
						$("<td>")
						    .addClass("title")
						    .html($("<label>").attr("for", "patient_address").html("Address")),
						$("<td>")
						    .addClass("editfield")
						    .append(
							$("<input>")
							    .attr("id","patient_address")
							    .attr("type","text")
							    .attr("tabindex","14")
							    .attr("name","patient_address")
							    .attr("style","width: 35%"),
							"&nbsp;Suburb&nbsp;",
							$("<input>")
							    .attr("id","patient_suburb")
							    .attr("type","text")
							    .attr("tabindex","15")
							    .attr("name","patient_suburb")
							    .attr("style","width: 25%"),
							"&nbsp;Postcode&nbsp;",
							$("<input>")
							    .attr("id","patient_postcode")
							    .attr("type","text")
							    .attr("tabindex","16")
							    .attr("name","patient_postcode")
							    .attr("style","width: 15%"))))
				    // change tabindex of main edit bar
				    $("#composebody").attr("tabindex","17");
				    load_from_subject();
				})
}
			      
						    
	
			     
