# represents a HL7 segment or a field with components, or a component with subcomponents

module HL7
  class Field
    attr_writer :separator
    attr_reader :separator
    
    # +values+ is a Hash of inital values for the field/segment
    def initialize(values=nil,separator='^',subseparator="&",rep_sep='~',esc="\\")
      @separator = separator
      @rep_sep = rep_sep
      @subseparator = subseparator
      @esc = esc
      @fields = Hash.new
      if ! values.nil?
        values.each do |x|
          field, value = x
          if field.is_a? Symbol
            field = get_by_sym field
          end
          @fields[field] = fields_desc[field][2].from_ruby(value)
          if @fields[field].respond_to?(:separator)  && @separator == '^' # we're a field, so it's a subfield
            @fields[field].separator = '&'
          end
        end
      end
    end
  
    # print out the field using pretty-printing style, called via +pp+
    def pretty_print(pp)
      pp.group(1) do
        fields_desc.each do |field|
          val = self.send(field[0])
          unless (val.respond_to?(:blank?) and val.blank?) or val.nil? or val == ''
            pp.breakable
            pp.text(field[0].to_s+':')
            pp.pp(val)
          end
        end
      end
    end
  
  
    #  - +fields+ is the line of HL7 source text to parse
    #  - +separator+ is the primary spearator in this context (| for segments, ^ for fields, & for components)
    #  - +subseparator+ is the next level (^ for segments, & for fields, nil for components)
    #  - +subsubseparator+, & for segments, otherwise nil
    #  - +rep_sep+ the repition separator (usually ~)
    #  - +esc+ is the HL7 escape char, usually \\
    def self.parse(fields, separator, subseparator, subsubseparator, rep_sep, esc)
      obj = new(nil,separator,subseparator,rep_sep,esc)
      fields = fields.split(separator)
      fields.each_with_index do |field, index|
        if ! field.empty?
          desc = obj.fields_desc[index]
          if ! desc.nil? # do we have a descriptor?
            kls = desc[2]
            if rep_sep && kls != Literal
              subfields = field.split(rep_sep)
              field = subfields.map {|x| 
                kls.parse(x,subseparator,subsubseparator,nil,nil,esc)
              }
              if ! obj.fields_desc[index][1] # if it's not a repeating field, dump the repeats if they exist
                field = field[0]
              end
            else
              field = kls.parse(field,subseparator,subsubseparator,nil,rep_sep,esc)
            end
            obj.set(index,field)
          end
        end
      end
      obj
    end
    
    # set a field to value +x+
    def set(index,x)
      if index.is_a? Symbol
        index = get_by_sym(index)
      end
      unless x.nil? or x == ''
        if fields_desc[index][1] # we're a repeating field
          x = [x] unless x.is_a? Array
          @fields[index] = x.map { |y| fields_desc[index][2].from_ruby(y)}
        else
          @fields[index] = fields_desc[index][2].from_ruby(x)
        end
        if @fields[index].respond_to?(:separator)  && @separator == '^' # we're a field, so it's a subfield
          @fields[index].separator = '&'
        end
      end
    end
  
    # get a field value, either by symbolic name or number
    def get(method)
      if method.is_a? Symbol
        @fields[get_by_sym(method)] || Blank.new
      elsif method.is_a? Integer
        return @fields[method] || Blank.new
      end
    end
    
    def [](x)
      get(x)
    end
  
    def []= (index, x)
      set(index,x)
    end
    
    # provides access to named fields via methods on the object
    def method_missing(method,val=nil)
      if val.nil?
        get(method)
      else
        method = method.to_s[0..-2].to_sym # get rid of = sign
        set(method,val)
      end
    end
    
    # converts to HL7 format
    def to_hl7
      f = @fields.dup
      f.default = ''
      s = ''
      i = 0
      until f.empty?
        s << @separator unless i == 0
        x =  f.delete(i)
        kls = fields_desc[i][2]
        if kls == Obx5
          s << x.to_s
        else
          if x
            if fields_desc[i][1] and x.kind_of? Array
              s << x.map {|y| kls.to_hl7(y)}.join(@rep_sep)
            else
              y = kls.to_hl7(x)
              if y.nil?
                y = ''
              end
              s << y
            end
          end
        end
        i += 1
      end
      s
    end
    
    def self.to_hl7(x)
      if x.respond_to? :to_hl7
        x.to_hl7
      else
        x.to_s
      end
    end
    
    # converts from a natural Ruby form (in this case, a Hash) to HL7 object representation
    def self.from_ruby(value)
      if value.is_a? Hash
        value = self.new(value)
      end
      value
    end
    
    # true if no values
    def blank?
      length == 0
    end
    
    # number of fields
    def length
      @fields.length
    end
    
    private
    
    def get_by_sym(sym)
      fields_desc.each_with_index do |x,i|
        if x[0] == sym
          return i
        end
      end
      raise HL7::Error, 'no such field %s' % sym.to_s
    end
  end
end
