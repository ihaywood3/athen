
# observation control. Basically redundant in modern use of HL7
module HL7
  class Orc < HL7::Segment
    def fields_desc
      [
        [:segment,false,Literal],
        [:order_control,false,Id],
        [:placer_order_number,false,Ei],
        [:filler_order_number,false,Ei],
        [:placer_group_number,false,Ei],
        [:order_status,false,Id],
        [:response_flag,false,Id],
        [:quantity_timing,false,Tq],
        [:parent,false,Eip],
        [:time_of_transaction,false,Ts],
        [:entered_by,true,Xcn],
        [:verified_by,true,Xcn],
        [:ordering_provider,true,Xcn],
        [:enterers_location,false,Pl],
        [:call_back,false,Xtn],
        [:order_effective_time,false,Ts],
        [:order_control_code_reason,false,Ce],
        [:entering_organisation,false,Ce],
        [:entering_device,false,Ce],
        [:action_by,true,Xcn],
        [:advanced_beneficiary_notice_code,false,Ce],
        [:ordering_facility_name,true,Xon],
        [:ordering_facility_address,true,Xad],
        [:ordering_facility_phone,true,Xtn],
        [:ordering_provider_address,true,Xad],
        [:order_status_modifier,false,Ce],
        [:advanced_beneficiary_notice_override_reason,false,Cwe],
        [:fillers_expected_availability_time,false,Ts],
        [:confidentiality_code,false,Cwe],
        [:order_type,false,Cwe],
        [:enterer_authorization_mode,false,Ce] # FIXME: should be CNE
      ]
    end
  end
end