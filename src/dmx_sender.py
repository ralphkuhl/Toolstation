import time
from pylibftdi import Device, FtdiError # Probeer FtdiError direct uit pylibftdi te halen

# DMX512 Parameters
DMX_BAUDRATE = 250000
DMX_BYTESIZE = 8
DMX_PARITY = 'N'  # None
DMX_STOPBITS = 2

# Timing for Break and MAB (in seconds)
BREAK_BAUDRATE = 90000
BREAK_DURATION_MIN = 88e-6 # Min Break duration
MAB_DURATION_MIN = 12e-6 # Min Mark After Break duration

DMX_START_CODE = 0x00

class DMXSender:
    def __init__(self, device_id=None, auto_open=True):
        self.device_id = device_id
        self.dev = None
        # Buffer: Start Code (1 byte) + 512 channels (512 bytes)
        self._dmx_buffer = bytearray([DMX_START_CODE] + [0] * 512)

        if auto_open:
            # Wrap open call to prevent program crash if FTDI device not found during __init__
            try:
                self.open()
            except Exception as e:
                print(f"DMXSender __init__: Failed to auto-open device '{self.device_id}': {e}")
                # self.dev remains None, subsequent calls to send_dmx will fail gracefully or error

    def open(self):
        if self.dev and self.dev.is_open:
            print(f"DMXSender: Device '{self.dev.device_id}' already open.")
            return

        try:
            self.dev = Device(device_id=self.device_id, mode='b') # mode='b' for bitbang/direct ftdi_fn access
            if not self.dev.is_open: # Should be opened by constructor
                 self.dev.open()

            self.dev.baudrate = DMX_BAUDRATE

            ftdi_parity = self._get_ftdi_parity_const(DMX_PARITY)
            ftdi_stopbits = self._get_ftdi_stopbits_const(DMX_STOPBITS)

            self.dev.ftdi_fn.ftdi_set_line_property(DMX_BYTESIZE, ftdi_stopbits, ftdi_parity)
            self.dev.ftdi_fn.ftdi_set_flowctrl(0) # No flow control

            print(f"DMXSender: FTDI Device '{self.dev.device_id}' opened and configured for DMX.")

        except FtdiError as e:
            self.dev = None # Ensure dev is None if open fails
            print(f"DMXSender: Error opening/configuring FTDI device '{self.device_id}': {e}")
            print("  Ensure libftdi drivers are installed and device is connected.")
            print("  On Windows, you might need Zadig to install libusb-based drivers for the FTDI device.")
            raise # Re-raise to signal failure to the caller (e.g. DMXController)
        except Exception as e:
            self.dev = None
            print(f"DMXSender: Unexpected error opening/configuring FTDI device '{self.device_id}': {e}")
            raise


    def _get_ftdi_parity_const(self, parity_char):
        if not self.dev: raise ConnectionError("FTDI device not open, cannot get parity constants.")
        if parity_char.upper() == 'N': return self.dev.ftdi_fn.NONE
        if parity_char.upper() == 'O': return self.dev.ftdi_fn.ODD
        if parity_char.upper() == 'E': return self.dev.ftdi_fn.EVEN
        raise ValueError(f"Unsupported parity: {parity_char}")

    def _get_ftdi_stopbits_const(self, stopbits):
        if not self.dev: raise ConnectionError("FTDI device not open, cannot get stopbit constants.")
        if stopbits == 1: return self.dev.ftdi_fn.STOP_BIT_1
        if stopbits == 2: return self.dev.ftdi_fn.STOP_BIT_2
        raise ValueError(f"Unsupported stop bits: {stopbits}")

    def set_channel(self, channel: int, value: int):
        if not (1 <= channel <= 512):
            raise ValueError("Channel number must be between 1 and 512.")
        if not (0 <= value <= 255):
            raise ValueError("Channel value must be between 0 and 255.")
        self._dmx_buffer[channel] = value # channel is 1-based, buffer[0] is start code

    def set_channels(self, start_channel: int, values: list[int]):
        if not (1 <= start_channel <= 512):
            raise ValueError("Start channel number must be between 1 and 512.")
        if not values: return
        if start_channel + len(values) - 1 > 512:
            raise ValueError("Too many values for the given start channel.")

        for i, value in enumerate(values):
            if not (0 <= value <= 255):
                raise ValueError(f"Channel value at index {i} (for DMX channel {start_channel+i}) must be between 0 and 255.")
            self._dmx_buffer[start_channel + i] = value

    def clear_all_channels(self):
        for i in range(1, 513): # DMX channels 1-512
            self._dmx_buffer[i] = 0

    def send_dmx(self):
        if not self.dev or not self.dev.is_open:
            # print("DMXSender: Device not open or available.") # Can be too noisy for a loop
            raise ConnectionError("DMXSender: FTDI device is not open or available for sending.")

        try:
            # 1. Send Break
            self.dev.baudrate = BREAK_BAUDRATE
            # Duration of 0x00 at BREAK_BAUDRATE (assume 8N2 = 11 bits): 11 / 90000 = ~122.2 µs. This is > 88µs.
            self.dev.write(b'\x00')
            time.sleep(30e-6) # Short pause to ensure byte is clocked out by FTDI. (Was 20e-6, 30e-6 is safer)

            # 2. Send Mark-After-Break (MAB)
            self.dev.baudrate = DMX_BAUDRATE
            # Re-assert DMX line properties (250k, 8N2) if changing them for break was necessary.
            # For now, assume properties persist through baudrate change.
            time.sleep(MAB_DURATION_MIN)

            # 3. Send Start Code and Channel Data
            self.dev.write(self._dmx_buffer)

        except FtdiError as e:
            print(f"DMXSender: Error during DMX send: {e}")
            # Consider how to handle this: re-raise, attempt reconnect, or mark as broken.
            raise # Re-raise for now, DMXController can decide how to handle.
        except Exception as e:
            print(f"DMXSender: Unexpected error during DMX send: {e}")
            raise

    def close(self):
        if self.dev and self.dev.is_open:
            try:
                # Optionally send a final blackout frame
                # self.clear_all_channels()
                # self.send_dmx()
                # time.sleep(0.05) # Allow frame to send
                self.dev.close()
                print(f"DMXSender: FTDI Device '{self.device_id or self.dev.device_id}' closed.")
            except FtdiError as e:
                print(f"DMXSender: Error closing FTDI device: {e}")
        self.dev = None # Ensure dev is None after close

    def __enter__(self):
        if not self.dev or not self.dev.is_open:
            self.open() # open() will raise if it fails
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == '__main__':
    # Add src directory to sys.path for direct execution testing
    import sys, os
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPT_DIR not in sys.path:
         sys.path.insert(0, _SCRIPT_DIR)
    # Note: This sys.path modification is for when this script itself is run directly.
    # It doesn't affect how other modules import this one.

    print("DMX Sender Test Script")
    sender = None
    try:
        try:
            from pylibftdi import Driver
            print("Attempting to list FTDI devices...")
            available_devices = Driver().list_devices()
            if available_devices:
                print("Available FTDI devices (vendor, product, serial):")
                for dev_info in available_devices:
                    print(f"- {dev_info}")
            else:
                print("No FTDI devices found by pylibftdi.Driver.")
        except Exception as e:
            print(f"Could not list devices: {e}")

        print("\nInitializing DMXSender...")
        # Using context manager for robust open/close
        with DMXSender() as sender: # auto_open=True is default
            print(f"Successfully initialized DMXSender with device: {sender.dev.device_id if sender.dev else 'None'}")
            if not sender.dev:
                print("Exiting test as DMXSender device could not be opened.")
                exit(1)

            print("Sending Channel 1 to 255, then to 0.")
            sender.set_channel(1, 255)
            sender.send_dmx()
            time.sleep(1)

            sender.set_channel(1, 0)
            sender.send_dmx()
            time.sleep(0.5)

            print("Sending a chase on channels 1-5 (2 iterations)...")
            for _ in range(2):
                for i in range(1, 6):
                    sender.clear_all_channels()
                    sender.set_channel(i, 200)
                    sender.send_dmx()
                    time.sleep(0.1)

            sender.clear_all_channels()
            sender.send_dmx()
            print("Test pattern complete.")
        # sender is automatically closed by __exit__ here

    except FtdiError as e:
        print(f"FTDI specific error encountered in DMXSender test script: {e}")
        print("Ensure FTDI device is connected and drivers (libusb via Zadig on Win) are correct.")
    except ConnectionError as e: # Raised by send_dmx if device not open
        print(f"Connection error in DMXSender test script: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in the DMXSender test script: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # If not using context manager, sender.close() would be here.
        # But context manager handles it.
        if sender and sender.dev and sender.dev.is_open:
             print("Error: Sender device was not closed properly by context manager - this shouldn't happen.")
             sender.close()
        print("DMX Sender Test Script Finished.")
