from lib.flash_spi import FLASH
from system.hexpansion.config import HexpansionConfig
from machine import SPI, Pin
import os
import app
from app_components import Menu, Notification, clear_background

# default location to mount the main flash device
MOUNTPATH = "/flopagon"
# menu item text for three options
main_menu_items = ["Mount", "Remove", "Format"]

class FlopagonApp(app.App):
    def __init__(self, config=None):
        # if this is run from the EEPROM then config will be a HexpansionConfig for whatever slot it's plugged into
        # if not then we assume it's plugged into slot 2 (right hand side) for testing the app
        if config == None:
            config = HexpansionConfig(2)
        self.config = config

        # Make a menu GUI widget with the mount, unmount and format options
        self.menu = Menu(self, main_menu_items, select_handler=self.select_handler, back_handler=self.back_handler)

        # create a handle for the notification
        self.notification = None

        # set up the chip select pin, it's the first high-speed IO pin on the hexpansion
        cspin = self.config.pin[0]
        cspin.init(cspin.OUT, value=1)
        self.cspins = (cspin,)

        # set up the SPI device, we specify all the pins and max out at 10MHz
        # SPI 2 is used for the CTX graphics driver, SPI1 can be used by python code
        self.hspi = SPI(1, 10000000, sck=self.config.pin[1], mosi=self.config.pin[2], miso=self.config.pin[3])

        # Create a handle on the flash object, if you watch the serial console you'll see
        #  1 chips detected. Total flash size 16MiB.
        # at this point if all is working
        self.flash = FLASH(self.hspi, self.cspins, cmd5=False)

        # run the app class init
        super().__init__()

    def select_handler(self, item, item_idx):
        # menu handler we try catch this whole thing to keep the code small for embedding in the EEPROM
        try:
            if item == "Mount":
                # mounts the device at the default location
                os.mount(self.flash, MOUNTPATH)
            elif item == "Remove":
                # unmounts (safely removes) the storage
                os.umount(MOUNTPATH)
            elif item == "Format":
                # Format the drive as FAT
                os.VfsFat.mkfs(self.flash)
            # if the try-catch hasn't jumped out yet then what we tried to do must have succeded
            self.notification = Notification(f"{item} succeded")
        except Exception as err:
            # let the user know something went wrong
            self.notification = Notification(f"{item} failed {err}")

    def back_handler(self):
        # no state is saved in the app just minimise when the user is done with their choices
        self.minimise()

    # ctx GUI stuff just taken from the examples
    def draw(self, ctx):
        clear_background(ctx)
        self.menu.draw(ctx)
        if self.notification:
            self.notification.draw(ctx)

    def update(self, delta):
        self.menu.update(delta)
        if self.notification:
            self.notification.update(delta)

__app_export__ = FlopagonApp
