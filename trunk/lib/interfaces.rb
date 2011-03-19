module Athen

  # base class for user-interfaces
  class CommonInterface

    def debug=(d)
      @debug = d
    end

    def logfile=(s)
      @logfile = s
    end

    # log a string, as part of routine operations
    def log(s)
      @logfile.write(s+'\n')
    end

    # log a string: when debugging
    def debug(s)
      log(s) if @debug 
    end

    # massive disastrous error
    def panic(s)
    end

    def ok_status()
    end
  end

  # very simple CLI interface
  class CliInterface < CommonInterface

    def log(s)
      super(s)
      puts s
    end

    def panic(s)
      STDERR.write("***ERROR***:" + s)
      exit 64
    end

  end
end
