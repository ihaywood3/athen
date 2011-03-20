require 'rubygems'
require 'fox16'
require 'interfaces'
require 'thread'

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
      @text = FXText.new(packer,:opts=>LAYOUT_FILL)
      @log = []
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
      # setup timer to handle messages from other threads
      app.addTimeout(500, method(:timer), :repeat => true)
    end
 	
    def timer(sender,selector,data)
      while not @iface.queue.empty?
        h = @iface.queue.pop
        log(h[:log]) if h.key? :log
        if h.key? :status
          @status.text = h[:log] if h.key? :log
          @status.textColor = case h[:status]
                when :ok then FXRGB(10,220,10) # green
                when :warning then FXRGB(220,220,10) # yellow
                when :bad then FXRGB(220,10,10) # red
          end
        end
      end
    end

    def log(s)
      lines = h[:log].split("\n")
      @log += lines
      @log = @log[-50..-1] if @log.length > 51
      @text.text = @log.join("\n")
    end

    def create
     super
     show(PLACEMENT_SCREEN)
    end

    def iface=(i)
      @iface = i
    end
  end


  # base class for dialogs
  class BaseDialog < FXDialogBox
    def setup
      @matrix = FXMatrix.new(self, 3, :opts => MATRIX_BY_COLUMNS|LAYOUT_FILL|LAYOUT_SIDE_TOP)
      @font = FXFont.new(FXApp.instance, "System", 8, :hints=>FXFont::System)
    end

    def text_field_row(lbl, comment)
      FXLabel.new(@matrix, lbl, :opts=>JUSTIFY_LEFT)
      style = LAYOUT_FILL_X|LAYOUT_FILL_COLUMN|TEXTFIELD_NORMAL
      if lbl[-7..-1] == 'assword'
        style = style|TEXTFIELD_PASSWD
      end
      field = FXTextField.new(@matrix, 50, :opts=>style)
      lbl1 = FXLabel.new(@matrix, comment, :opts=>JUSTIFY_LEFT|LAYOUT_FILL_X|LAYOUT_SIDE_TOP|LAYOUT_FILL_COLUMN)
      lbl1.font = @font
      return field
    end
    
  end

  # from FXRuby examples page at http://www.fxruby.org/examples/dialog.rb with modifications
  class ConfigureDialog < BaseDialog
  
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
      setup
      @fields = Hash.new
      @fields[:smtp_host] = text_field_row("SMTP Host", "The server provided by your ISP or e-mail\nprovider to send e-mails out")
      @fields[:smtp_user] = text_field_row("SMTP Username","Username to log on to\nthe SMTP host, optional")
      @fields[:smtp_password] = text_field_row("SMTP Password","Password to log on to\nthe SMTP host, optional")
      
      @fields[:error_email] = text_field_row("Error E-mail","E-mail to send error reports to")
      @fields[:imap_host] = text_field_row("IMAP Host", "The server provided by your ISP or e-mail\nprovider to receive e-mails")
      @fields[:imap_user] = text_field_row("IMAP Username","Username to log on to\nthe IMAP host, optional")
      @fields[:imap_password] = text_field_row("IMAP Password","Password to log on to\nthe IMAP host, optional")
      @fields[:upload_dir] = dir_field_row("Upload directory","The directory where ATHEN finds files for upload")
      @fields[:download_dir] = dir_field_row("Download directory","The directory where ATHEN saves incoming files")
      @fields[:ack_dir] = dir_field_row("ACK directory","The directory where ACK files are found\nLeave blank if not used")
      @fields.each_pair { |k,v| v.text = $cfg[k] if $cfg[k] }
      # Accept
      accept = FXButton.new(buttons, "&Accept", :opts=>FRAME_RAISED|FRAME_THICK|LAYOUT_RIGHT|LAYOUT_CENTER_Y)
      accept.connect(SEL_COMMAND, method(:save))
      # Cancel
      cancel =  FXButton.new(buttons, "&Cancel", :opts=>FRAME_RAISED|FRAME_THICK|LAYOUT_RIGHT|LAYOUT_CENTER_Y)
      cancel.connect(SEL_COMMAND) { self.close }
      accept.setDefault  
      accept.setFocus
    end


    def dir_field_row(lbl, comment)
      FXLabel.new(@matrix, lbl, :opts=>JUSTIFY_LEFT)
      hbox = FXHorizontalFrame.new(@matrix,:opts=>LAYOUT_FILL_X|LAYOUT_FILL_COLUMN)
      field = FXTextField.new(hbox, 50, :opts=> LAYOUT_FILL_X|TEXTFIELD_NORMAL)
      btn = FXButton.new(hbox,"Find...",:opts=>FRAME_RAISED|FRAME_THICK)
      lbl1 = FXLabel.new(@matrix, comment, :opts=>JUSTIFY_LEFT|LAYOUT_FILL_X|LAYOUT_SIDE_TOP|LAYOUT_FILL_COLUMN)
      lbl1.font = @font
      btn.connect(SEL_COMMAND) do
        d = FXDirDialog.getOpenDirectory(self,lbl,field.text or "")
        field.text = d if d
      end
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
      @queue = Queue.new
    end

   def GuiInterface.run
      FXApp.new do |app|
 	main_window = MainWindow.new(app)
        main_window.iface = GuiInterface.new(main_window,app)
        app.create
        app.run
      end
   end
   
   def queue
     @queue
   end
   
   def log(s)
     @queue.push {:log=>s}
   end

   def status(s,m)
     @queue.push {:log=>m,:status=>s}
   end
  end
end
