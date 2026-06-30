from lib.flash_spi import FLASH
from system.hexpansion.config import HexpansionConfig
from system.eventbus import eventbus
from machine import SPI
import vfs
import app
import sys
from system.launcher.app import AppDirAddedNotificationEvent, AppDirRemovedNotificationEvent
from app_components import Menu, Notification, clear_background
from system.scheduler.events import RequestForegroundPushEvent

# default location to mount the main flash device
MOUNTPATH = "/flopagon"
APPDIR = "/floppy_apps"

# menu item text for three options
main_menu_items = ["Mount", "Remove", "Format"]

class FlopagonApp(app.App):
    def __init__(self, config=None):
        self.config = config

        # Make a menu GUI widget with the mount, unmount and format options
        self.menu = Menu(self, main_menu_items, select_handler=self.select_handler, back_handler=self.back_handler)

        # create a handle for the notification
        self.notification = None

        # create a flag to request foreground exactly once
        self.foregrounded = False

        # set up the chip select pin, it's the first high-speed IO pin on the hexpansion
        cspin = self.config.pin[0]
        cspin.init(cspin.OUT, value=1)
        self.cspins = (cspin,)

        for _ in range(2):
            # set up the SPI device, we specify all the pins and max out at 10MHz
            # SPI 2 is used for the CTX graphics driver, SPI1 can be used by python code
            self.hspi = SPI(1, 10000000, sck=self.config.pin[1], mosi=self.config.pin[2], miso=self.config.pin[3])

            # Create a handle on the flash object, if you watch the serial console you'll see
            #  1 chips detected. Total flash size 16MiB.
            # at this point if all is working
            try:
                self.flash = FLASH(self.hspi, self.cspins, cmd5=False)
                break
            except ValueError:
                # deinit and try again
                self.hspi.deinit()

        self.mounted = False

        # run the app class init
        super().__init__()

    def deinit(self):
        if self.mounted:
            vfs.umount(MOUNTPATH)
            if MOUNTPATH in sys.path:
                del sys.path[sys.path.index(MOUNTPATH)]
            eventbus.emit(AppDirRemovedNotificationEvent(MOUNTPATH+APPDIR))
            self.mounted = False
            self.hspi.deinit()

    def select_handler(self, item, item_idx):
        # menu handler we try catch this whole thing to keep the code small for embedding in the EEPROM
        try:
            if item == "Mount":
                # mounts the device at the default location
                vfs.mount(self.flash, MOUNTPATH)
                sys.path.append(MOUNTPATH)
                eventbus.emit(AppDirAddedNotificationEvent(MOUNTPATH+APPDIR))
                self.mounted = True
            elif item == "Remove":
                # unmounts (safely removes) the storage
                self.deinit()
            elif item == "Format":
                # Format the drive as FAT
                vfs.VfsFat.mkfs(self.flash)
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
        if not self.foregrounded: # Bring the app to the foreground on first run
            eventbus.emit(RequestForegroundPushEvent(self))
            self.foregrounded = True
        
        self.menu.update(delta)
        if self.notification:
            self.notification.update(delta)

__app_export__ = FlopagonApp
