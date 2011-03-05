module Athen

  # base class for user-interfaces
  class CommonInterface

    def debug=(d)
      @debug = d
    end

    # log a string, as part of routine operations
    def log(s)
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
    def initialize
      @panicked = false
    end

    def log(s)
      puts s
    end

    def panic(s)
      @panicked  = true
      log("***ERROR***:" + s)
    end

    def panicked
      @panicked
    end
  end
end
