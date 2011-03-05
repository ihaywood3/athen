require 'rubygems'
require 'fox16'
require 'interfaces'
include Fox

module Athen
  class MainWindow < FXMainWindow
    def initialize(app)
      super(app, "ATHEN", :width => 600, :height => 400)
      packer = FXPacker.new(self, :opts => LAYOUT_FILL)
      hframe1 = FXHorizontalFrame.new(packer,
                                     :opts => LAYOUT_SIDE_TOP|LAYOUT_FILL_X)
      lbl1 = FXLabel.new(hframe1, "Status:",
                  :opts => LAYOUT_LEFT)
      @status = FXButton.new(hframe1, "OK",
                            :opts => LAYOUT_LEFT)
      font = FXFont.new(app, "System", 16, :weight=>FXFont::Bold, :hints=>FXFont::System)
      lbl1.font = font
      @status.font = font
      @status.textColor = FXRGB(10,220,10)
      @text = FXText.new(packer,
                         :opts=>LAYOUT_FILL)
      hframe2 = FXHorizontalFrame.new(packer,
                                     :opts => LAYOUT_SIDE_BOTTOM|LAYOUT_FILL_X)
      download_now = FXButton.new(hframe2, "Download Now",:opts => BUTTON_NORMAL|BUTTON_AUTOGRAY|LAYOUT_LEFT)
      config = FXButton.new(hframe2, "Configure...",:opts => BUTTON_NORMAL|LAYOUT_LEFT)
      config.connect(SEL_COMMAND) { 
        @dialog = ConfigureDialog.new(app)
        @dialog.create
        @dialog.show(PLACEMENT_SCREEN)
      }
      verify = FXButton.new(hframe2, "Verify Key...",:opts => BUTTON_NORMAL|LAYOUT_LEFT)
      quit = FXButton.new(hframe2, "Quit",:opts => BUTTON_NORMAL|LAYOUT_LEFT)
      quit.connect(SEL_COMMAND) { app.stop }
      quit.tipText = "Exits the program"
      #download_now.connect(SEL_UPDATE) { true }
    end
 	

    def bad_status(s)
      @status.textColor = FXRGB(10,220,10)
      @status.text = s
    end

    def ok_status()
      @status.textColor = FXRGB(10,220,10)
      @status.text = "OK"
    end

    def create
     super
     show(PLACEMENT_SCREEN)
    end

    def iface=(i)
      @iface = i
    end
  end


  # from FXRuby examples page at http://www.fxruby.org/examples/dialog.rb with modifications
  class ConfigureDialog < FXDialogBox
  
    def initialize(owner)

      super(owner, "Configure ATHEN", DECOR_TITLE|DECOR_BORDER)

      # Bottom buttons
      buttons = FXHorizontalFrame.new(self,
        LAYOUT_SIDE_BOTTOM|FRAME_NONE|LAYOUT_FILL_X|PACK_UNIFORM_WIDTH,
        :padLeft => 40, :padRight => 40, :padTop => 20, :padBottom => 20)

      # Separator
      FXHorizontalSeparator.new(self,
        LAYOUT_SIDE_BOTTOM|LAYOUT_FILL_X|SEPARATOR_GROOVE)
  
      # Contents
      @matrix = FXMatrix.new(self, 3, :opts => MATRIX_BY_COLUMNS|LAYOUT_FILL|LAYOUT_SIDE_TOP)
      @font = FXFont.new(FXApp.instance, "System", 8, :hints=>FXFont::System)
      smtp_host = text_field_row("SMTP Host", "The server provided by your ISP or e-mail\nprovider to send e-mails out")
      smtp_user = text_field_row("SMTP Username","Username to log on to\nthe SMTP host, optional")
      smtp_password = text_field_row("SMTP Password","Password to log on to\nthe SMTP host, optional")
      error_email = text_field_row("Error E-mail","E-mail to send error reports to")
      FXLabel.new(@matrix, "Protocol", :opts=>JUSTIFY_LEFT)
      field = FXTextField.new(@matrix, 50, :opts=>style)
      lbl1 = FXLabel.new(@matrix, "Protocol ", :opts=>JUSTIFY_LEFT|LAYOUT_FILL_X|LAYOUT_FILL_COLUMN)
      lbl1.font = @font
      # Accept
      accept = FXButton.new(buttons, "&Accept", :opts=>FRAME_RAISED|FRAME_THICK|LAYOUT_RIGHT|LAYOUT_CENTER_Y)
      accept.connect(SEL_COMMAND, method(:save))
      # Cancel
      cancel =  FXButton.new(buttons, "&Cancel", :opts=>FRAME_RAISED|FRAME_THICK|LAYOUT_RIGHT|LAYOUT_CENTER_Y)
      cancel.connect(SEL_COMMAND) { self.close }
      accept.setDefault  
      accept.setFocus
    end


    def text_field_row(lbl, comment)
      FXLabel.new(@matrix, lbl, :opts=>JUSTIFY_LEFT)
      style = LAYOUT_FILL_X|LAYOUT_FILL_COLUMN|TEXTFIELD_NORMAL
      if lbl[-7..-1] == 'assword'
        style = style|TEXTFIELD_PASSWD
      end
      field = FXTextField.new(@matrix, 50, :opts=>style)
      lbl1 = FXLabel.new(@matrix, comment, :opts=>JUSTIFY_LEFT|LAYOUT_FILL_X|LAYOUT_FILL_COLUMN)
      lbl1.font = @font
      return field
    end

    def save(sender,mode,data)
      self.close
    end
  end

  class GuiInterface < CommonInterface

    def initialize(mw,a)
      @log = []
      @app = a
      @main_window = mw
    end

   def GuiInterface.run
      FXApp.new do |app|
 	main_window = MainWindow.new(app)
        main_window.iface = GuiInterface.new(main_window,app)
        app.create
        app.run
      end
   end

    def log(s)
      lines = s.split("\n")
      @log += lines
      @log = @log[-50..-1] if @log.length > 51
      @main_window.display_log(@log)
    end

    def panic(s)
      FXMessageBox.error(@app,MBOX_OK,"Error",s)
      l = s.split("\n")
      @main_window.badstatus(l.first)
    end

    def ok_status()
      @main_window.ok_status()
    end

  end
end
