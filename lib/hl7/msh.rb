# message header
module HL7
  class Msh < HL7::Segment
    def fields_desc
      [
        [:segment,false,Literal],
        [:encoding_characters,false,Literal],
        [:sending_application,false,Hd],
        [:sending_facility,false,Hd],
        [:receiving_application,false,Hd],
        [:receiving_facility,false,Hd],
        [:datetime_of_message,false,HL7DateTime],
        [:security,false,St],
        [:message_type,false,MessageType],
        [:message_control_id,false,St],
        [:processing_id,false,Pt],
        [:version_id,false,Vid],
        [:sequence_number,false,Nm],
        [:continuation_pointer,false,St],
        [:accept_acknowledgement_type,false,Id],
        [:application_acknowledgement_type,false,Id],
        [:country_code,false,Id],
        [:character_set,true,Id],
        [:principal_language_of_message,false,Id],
        [:alternative_character_set_handling_scheme,false,Id],
        [:message_profile_identifier,true,Ei]
      ]
    end
  end
end