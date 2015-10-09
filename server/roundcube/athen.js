
/*
** Plugin custom_from for RoundcubeMail
**  - Plugin script
*/

if (window.rcmail)
{
    var save_to_subject = function (event)
    {
	debugger;
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
							    .attr("style","width: 35%"),
							"&nbsp;Surname&nbsp;",
							$("<input>")
							    .attr("id","patient_surname")
							    .attr("type","text")
							    .attr("name","patient_firstname")
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
							    .attr("name","patient_dob")
							    .attr("style","width: 8em"),
							"&nbsp;",
							$("<input>")
							    .attr("id","sex_male")
							    .attr("type","radio")
							    .attr("name","sex")
							    .attr("value","male")
							    .attr("style","width: auto"),
							$("<label>").attr("for","sex_male").html("Male&nbsp;"),
							$("<input>")
							    .attr("id","sex_female")
							    .attr("type","radio")
							    .attr("name","sex")
							    .attr("value","female")
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
							    .attr("name","patient_address")
							    .attr("style","width: 35%"),
							"&nbsp;Suburb&nbsp;",
							$("<input>")
							    .attr("id","patient_suburb")
							    .attr("type","text")
							    .attr("name","patient_suburb")
							    .attr("style","width: 25%"),
							"&nbsp;Postcode&nbsp;",
							$("<input>")
							    .attr("id","patient_postcode")
							    .attr("type","text")
							    .attr("name","patient_postcode")
							    .attr("style","width: 15%"))))
						
				})
}
			      
						    
	
			     
