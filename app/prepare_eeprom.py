from machine import I2C
from system.hexpansion.header import HexpansionHeader, write_header
from system.hexpansion.util import (
    detect_eeprom_addr,
    get_hexpansion_block_devices,
    read_hexpansion_header,
)
import vfs
import shutil

# Fill in your desired header info here:
# use this one for the M24C16:
header_flopagon_v1 = HexpansionHeader(
    manifest_version="2024",
    fs_offset=32,
    eeprom_page_size=16,
    eeprom_total_size=1024 * (16 // 8),
    vid=0xCAFE,
    pid=0xD15C,
    unique_id=0,
    friendly_name="Flopagon",
)

header_flopagon_v2 = HexpansionHeader(
    manifest_version="2024",
    fs_offset=32,
    eeprom_page_size=32,
    eeprom_total_size=1024 * (64 // 8),
    vid=0xCAFE,
    pid=0xD15D,
    unique_id=0,
    friendly_name="Flopagon2",
)

def setup_flopagon(port):
    _prepare_generic(port, header_flopagon_v1)

def setup_flopagon_v2(port):
    _prepare_generic(port, header_flopagon_v2)

def _prepare_generic(port, header):
    # Set up i2c
    i2c = I2C(port)

    # autodetect eeprom address
    addr, addr_len = detect_eeprom_addr(i2c)
    print(f"Detected eeprom at {hex(addr)}")

    # Write and read back header
    write_header(
        port, header, addr=addr, addr_len=addr_len, page_size=header.eeprom_page_size
    )
    header = read_hexpansion_header(i2c, addr, set_read_addr=True, addr_len=addr_len)

    if header is None:
        raise RuntimeError("Failed to read back hexpansion header")

    # Get block devices
    eep, partition = get_hexpansion_block_devices(i2c, header, addr, addr_len=addr_len)

    # Format
    vfs.VfsLfs2.mkfs(partition)

    # And mount!
    vfs.mount(partition, "/eeprom")

    # and copy the app
    with open("app.mpy", "rb") as fr:
        with open("/eeprom/app.mpy", "wb") as fw:
            shutil.copyfileobj(fr, fw)