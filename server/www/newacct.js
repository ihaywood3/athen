var specialties = 
    {
	med: ["GP","RMO","Registrar","Surgeon","Physician","Psychiatrist","Dermatologist","Pathologist","Gynaecologist","Radiologist"],
	allied: ["Psychologist","Social worker","Physiotherapist","Occupational therapist","Dietitian","Podiatrist","Optometrist"],
	dentist:["General Dentist","Oral Physician","Maxillo-facial Surgeon","Prosthodontist","Orthodontist","Endodontist","Dental radiologist","Dental pathologist","Periodontist","Forensic dentist","Paediatric dentist","Oral surgeon"],
	physician:["Cardiologist","Haematologist","Paediatrician","Geriatrician","Respiratory physician","General physician","Rheumatologist","Gastroenterologist","Neurologist","Nuclear medicine physician","ICU Physician","Rehabilitation Physician","Palliative physician","Geneticist","Endocrinologist","Immunologist","ID physician","Renal physician"],
	surgeon:["General Surgeon","Vascular Surgeon,","Orthopaedic Surgeon","Neurosurgeon","ENT Surgeon","Plastic Surgeon","Ophthalmologist","Cardiothoracic Surgeon","Urologist"],
	psychiatrist:["General Psychiatrist","Child Psychiatrist","Old-Age Psychiatrist","Forensic Psychiatrist","Psychotherapist","Neuropsychiatrist"],
	gynaecologist:["Obstetrician","Gynaecologist Only","Maternal foetal medicine","Urogynaecologist","Gynaeoncologist","IVF"],
	registrar:["Medical registrar","Surgical registrar","GP registrar","Psychiatry registrar","Dermatology registrar","Pathology Registrar","OG registrar","Radiology registrar"],
	psychologist:["Clinical psychologist","Counselling psychologist","Forensic psychologist","Educational psychologist","Neuropsychologist"],
    };

$(document).ready(function(){
    // jQuery code, event handling callbacks here
    var radioPerson = $("input#radioperson");
    var radioOrg = $("input#radioorg");
    var selectProf = $("select#profession");
    var selectSpec = $("select#specialty");
    var selectSub = $("select#subspecialty");

    $("tr#rowspecialty").hide();
    $("tr#rowsubspecialty").hide();

    selectProf.on("change", function (event) {
	var val = selectProf.val();

	selectSpec.empty();
	selectSub.empty();
	if (val in specialties) {
	    $("tr#rowspecialty").show();
	    var a = specialties[val];
	    a.sort();
	    for (i in a) {
		var s = a[i];
		selectSpec.append($('<option />').attr({value:s.toLowerCase()}).append(s));
	    }
	} else { $("tr#rowspecialty").hide (); }
    });

    selectSpec.on("change", function (event) {
	var val = selectSpec.val();

	selectSub.empty();
	if (val in specialties) {
	    $("tr#rowsubspecialty").show();
	    for (i in specialties[val]) {
		var s = specialties[val][i];
		selectSub.append($('<option />').attr({value:s.toLowerCase()}).append(s));
	    }
	} else { $("tr#rowsubspecialty").hide (); }
    });
   radioOrg.on("change",function (event) {
	if (! radioOrg.checked) {
	    $("tr.person").hide();
	    $("tr.org").show();
	}
    });
    radioPerson.on("change",function (event) {
	if (! radioPerson.checked) {
	    $("tr.person").show();
	    $("tr.org").hide();
	    $("tr#rowspecialty").hide();
	    $("tr#rowsubspecialty").hide();
	}
    });
});
