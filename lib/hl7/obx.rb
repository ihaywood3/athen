# Observation, by far the most important segment
module HL7
  class Obx < HL7::Segment
    def fields_desc
      [
        [:segment,false,Literal],
        [:set_id,false,Si],
        [:value_type,false,Id],
        [:identifier,false,Ce],
        [:subidentifier,false,St],
        [:value,true,Obx5],
        [:unit,false,Ce],
        [:reference_range,false,St],
        [:abnormal_flags,true,Is],
        [:probability,false,Nm],
        [:nature_of_abnormal_test,true,Id],
        [:result_status,false,Id],
        [:effective_date_of_reference_range,false,Ts],
        [:user_defined_access_checks,false,St],
        [:time,false,Ts],
        [:producers_id,false,Ce],
        [:responsible_observer,true,Xcn],
        [:observation_method,true,Ce],
        [:equipment,true,Ei],
        [:time_analysis,false,Ts]
      ]
    end
    
    # this is a "magic" HL7 field and it's parsing type depends on OBX-2
    def value
      val = get(:value)
      vals = val.to_s.split(@rep_sep)
      begin
        kls = eval("#{value_type.capitalize}")
      rescue NameError
        raise HL7::Error, "Unknown OBX-5 type: #{value_type}"
      end
      vals.map! {|x| kls.parse(x,@subseparator,@subsubseparator,nil,nil,@esc)}
      if kls == St # repeating strings mean newlines. Yes, it does. Read the spec.
        vals.join("\n") 
      else
        vals
      end
    end
    
    def value=(x)
      begin
        kls = eval("#{value_type.capitalize}")
      rescue NameError
        raise HL7::Error, "Unknown OBX-5 type: #{value_type}"
      end
      if x.kind_of? Array
        x.map! {|y| kls.to_hl7(kls.from_ruby(y))}
        x = x.join(@rep_sep)
      else
        x = kls.to_hl7(kls.from_ruby(x))
      end
      @fields[5] = x
    end
  
    # attempt to return as HTML, only for text-type fields.
    def value_as_html
      v = value
      if v.is_a? Array
        return "" if v.length == 0
        v = v[0]
      end
      return "" if v.nil?
      v = v.to_s unless v.is_a? String
      v.gsub!("\n\n","<p/>")
      v.gsub(/^( *)(.*)/) { |m| n = $1; m = $2; n="" unless n ; m="" unless m; n.gsub!(" ","&nbsp;") ; if m.length < 70 then;  n+m+"<br/>" else n+m ; end}
    end
  end
end
