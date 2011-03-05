# Patient IDentification
module HL7
  class HL7::Pid < HL7::Segment
    def fields_desc
      [
        [:segment,false,Literal],
        [:set_id,false,Si],
        [:patient_id,false,Cx],
        [:patient_identifier_list,true,Cx],
        [:alternate_patient_id,false,Cx],
        [:patient_name,true,Xpn],
        [:mothers_maiden_name,true,Xpn],
        [:date_of_birth,false,Ts],
        [:sex,false,Is],
        [:alias,true,Xpn],
        [:race,false,Ce],
        [:patient_address,true,Xad],
        [:county,false,Is],
        [:home_phone,true,Xtn],
        [:work_phone,true,Xtn],
        [:primary_language,false,Ce],
        [:marital_status,false,Ce],
        [:religion,false,Ce],
        [:account_number,false,Cx],
        [:ssn,false,St],
        [:drivers_licence,false,St],
        [:mother,false,Cx],
        [:ethicity,false,Ce],
        [:birth_place,false,St],
        [:multiple_birth,false,Id],
        [:birth_order,false,Nm],
        [:citizenship,true,Ce],
        [:veteran,true,Ce], # not used
        [:nationality,true,Ce],
        [:death,false,Ts],
        [:death_indicator,false,Id],
        [:unknown,false,Id],
        [:identity_reliability_code,false,Id],
        [:last_update,false,Ts],
        [:last_update_facility,false,Hd],
        [:species,false,Ce], # vet fields
        [:breed,false,Ce],
        [:strain,false,St],
        [:production_class_code,false,Ce],
        [:tribe,false,Cwe]
      ]
    end
  end
end