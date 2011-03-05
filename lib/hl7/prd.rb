# PRovider Data
module HL7
  class HL7::Prd < HL7::Segment
    def fields_desc
      [
        [:segment,false,Literal],
        [:role,true,Ce],
        [:name,true,Xpn],
        [:address,true,Xad],
        [:location,false,Pl],
        [:communication_information,true,Xtn],
        [:preferred_contact_method,false,Ce], # table 185
        [:provider_identifiers,true,Prd7],
        [:start_date_provider_role,false,Ts],
        [:end_date_provider_role,false,Ts]
      ]
    end
  end
end
