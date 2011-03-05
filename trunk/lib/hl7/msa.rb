module HL7
  # message acknowledgement
  class Msa < HL7::Segment
    def fields_desc
    [
      [:segment,false,Literal],
      [:code,false,Id],
      [:control_id,false,St],
      [:text,false,St],
      [:number,false,Nm],
      [:delayed_ack_type,false,St], # deprecated to the point that the 2.5 docs refuse to tell us what type it was!
      [:error_condition,false,Ce]
    ]
    end
  end
end