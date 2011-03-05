# Referral Information 1
module HL7
  class Rf1 < HL7::Segment
    def fields_desc
      [
        [:segment,false,Literal],
        [:status,false,Ce], # table 283
        [:priority,false,Ce], # table 280
        [:referral_type,false,Ce], # table 281
        [:disposition,true,Ce], # table 282
        [:category,false,Ce], # table 284
        [:originating_referral_identifier,false,Ei], 
        [:effective_date,false,Ts],
        [:expiration_date,false,Ts],
        [:process_date,false,Ts],
        [:referral_reason,true,Ce],
        [:external_identifier,true,Ei]
      ]
    end
  end
end
      
