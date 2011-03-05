# Patient Visit 1 (there is a Patient Visit 2)
# few of these fields have any relevence for Australia use.

module HL7
  class Pv1 < HL7::Segment
    def fields_desc
      [
        [:segment,false,Literal],
        [:set_id,false,Si],
        [:patient_class,false,Is],
        [:assigned_patient_location,false,Pl],
        [:admission_type,false,Is],
        [:preadmit_number,false,Cx],
        [:prior_patient_location,false,Pl],
        [:attending_doctor,false,Xcn],
        [:referring_doctor,false,Xcn],
        [:consulting_doctor,false,Xcn],
        [:hospital_service,false,Is],
        [:temporary_location,false,Pl]
        # FIXME: many more fields in standard, but unlikely to be used by us
      ]
    end
  end
end