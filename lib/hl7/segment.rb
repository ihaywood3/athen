module HL7
# HL7 segment
  class Segment < HL7::Field
  
    def initialize(values=nil,separator='|',subseparator='^',rep_sep='~',esc="\\")
      super(values,separator,subseparator,rep_sep,esc)
    end
  
    attr_writer :parent
    attr_writer :no
  
    # search for segments after this segment of type +seg+,
    # stopping at the next encounter of this segment.
    def sub(seg,&blk)
      @parent.each(seg,@no,@seg_type,&blk)
    end
  
  end
end