import sys
import os
import time
import threading

# If running this script directly, add the 'src' directory to sys.path
# to allow imports of sibling modules (like dmx_sender).
# This needs to be done before the attempt to import dmx_sender.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from dmx_sender import DMXSender, FtdiError # Directe import

class DMXController:
    def __init__(self, device_id=None, auto_start_thread=True, update_rate_hz=40):
        """
        Manages the DMX universe and sends data using DMXSender.
        :param device_id: Optional serial ID of the FTDI device.
        :param auto_start_thread: If True, starts the DMX sending thread automatically.
        :param update_rate_hz: Target DMX update rate in Hz (e.g., 40Hz).
        """
        self.dmx_sender = None # Initialize to None
        self._dmx_values = bytearray(512)  # Kanaal 1 = index 0, Kanaal 512 = index 511

        self.is_running = False
        self._dmx_thread = None
        self._thread_lock = threading.Lock()

        if update_rate_hz <= 0:
            raise ValueError("update_rate_hz must be positive.")
        self.update_interval = 1.0 / update_rate_hz

        try:
            # Initialize DMXSender here. If it fails, dmx_sender remains None.
            self.dmx_sender = DMXSender(device_id=device_id, auto_open=True) # auto_open=True in DMXSender handles opening
            print("DMXController: DMXSender initialized successfully.")
        except FtdiError as e:
            print(f"DMXController: Failed to initialize DMXSender: {e}")
            # self.dmx_sender remains None
        except Exception as e:
            print(f"DMXController: Unexpected error during DMXSender initialization: {e}")
            # self.dmx_sender remains None

        if auto_start_thread and self.dmx_sender:
            self.start_dmx_output()

    def set_channel(self, channel: int, value: int):
        if not (1 <= channel <= 512):
            raise ValueError("Channel must be between 1 and 512.")
        if not (0 <= value <= 255):
            raise ValueError("Value must be between 0 and 255.")

        with self._thread_lock:
            self._dmx_values[channel - 1] = value

    def set_channels(self, start_channel: int, values: list[int]):
        if not (1 <= start_channel <= 512):
            raise ValueError("Start channel must be between 1 and 512.")
        if not values:
            return
        if start_channel + len(values) -1 > 512:
            raise ValueError("Too many values for the given start channel, exceeds 512 channels.")

        with self._thread_lock:
            for i, val in enumerate(values): # Renamed value to val to avoid conflict
                if not (0 <= val <= 255):
                    raise ValueError(f"Value at index {i} (for channel {start_channel+i}) is out of range (0-255).")
                self._dmx_values[start_channel + i - 1] = val

    def get_channel(self, channel: int) -> int:
        if not (1 <= channel <= 512):
            raise ValueError("Channel must be between 1 and 512.")
        with self._thread_lock:
            return self._dmx_values[channel - 1]

    def get_all_values(self) -> bytearray:
        with self._thread_lock:
            return self._dmx_values[:] # Return a copy

    def clear_all_channels(self):
        with self._thread_lock:
            for i in range(512):
                self._dmx_values[i] = 0

    def blackout(self):
        self.clear_all_channels()
        # The running thread will pick up the zeroed values.
        # If not running, values are zeroed for when it starts.

    def _dmx_send_loop(self):
        while self.is_running:
            if self.dmx_sender: # Check if sender was successfully initialized
                temp_dmx_values_copy = self.get_all_values() # Get a thread-safe copy

                # Pass the entire 512 channel values to DMXSender's set_channels method.
                # DMXSender's set_channels(1, list_of_512_values) will update its internal buffer.
                try:
                    self.dmx_sender.set_channels(1, list(temp_dmx_values_copy))
                    self.dmx_sender.send_dmx()
                except FtdiError as e:
                    print(f"DMXController: Error during DMX send in loop: {e}. Stopping output.")
                    # Potentially stop the thread or attempt to re-initialize sender
                    self.is_running = False # Stop the loop on send error
                    break
                except Exception as e:
                    print(f"DMXController: Unexpected error in send loop: {e}. Stopping output.")
                    self.is_running = False # Stop the loop
                    break
            else:
                # DMX sender not available, cannot send.
                # This case should ideally be handled by not starting the thread
                # or stopping it if dmx_sender becomes None later.
                print("DMXController: DMX sender not available in send loop. Stopping output.")
                self.is_running = False # Stop the loop
                break

            time.sleep(self.update_interval)

        if self.dmx_sender:
            try:
                print("DMXController: Sending final blackout frame as thread stops.")
                self.dmx_sender.clear_all_channels()
                self.dmx_sender.send_dmx()
            except Exception as e:
                print(f"DMXController: Error sending final blackout: {e}")


    def start_dmx_output(self):
        if not self.dmx_sender:
            print("DMXController: Cannot start output, DMXSender not initialized or failed to initialize.")
            return

        if self.is_running:
            print("DMXController: DMX output thread already running.")
            return

        self.is_running = True
        self._dmx_thread = threading.Thread(target=self._dmx_send_loop, daemon=True)
        self._dmx_thread.name = "DMXControllerThread"
        self._dmx_thread.start()
        print("DMXController: DMX output thread started.")

    def stop_dmx_output(self):
        if not self.is_running:
            # print("DMXController: DMX output thread is not running.") # Can be noisy
            return

        self.is_running = False
        if self._dmx_thread and self._dmx_thread.is_alive():
            print("DMXController: Attempting to join DMX output thread...")
            self._dmx_thread.join(timeout=self.update_interval * 10)
            if self._dmx_thread.is_alive():
                print("DMXController: Warning - DMX thread did not terminate gracefully after timeout.")
            else:
                print("DMXController: DMX output thread joined successfully.")
        self._dmx_thread = None
        # print("DMXController: DMX output thread stopped.") # Covered by join message

    def close(self):
        print("DMXController: close() called.")
        self.stop_dmx_output() # Ensure thread is stopped first
        if self.dmx_sender:
            print("DMXController: Closing DMXSender...")
            self.dmx_sender.close()
            print("DMXController: DMXSender closed.")
        self.dmx_sender = None # Ensure it's None after closing

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # __del__ can be problematic with threads, rely on explicit close or context manager

if __name__ == '__main__':
    import sys
    import os
    # If running this script directly, add the 'src' directory to sys.path
    # to allow imports of sibling modules (like dmx_sender).
    if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # Her-importeer DMXSender en FtdiError hieronder expliciet als dat nodig is voor het __main__ blok,
    # maar de import bovenaan het bestand zou nu moeten werken voor de klasse DMXController.
    # De klasse DMXController zelf zou nu moeten kunnen importeren.

    print("DMX Controller Test Script")
    # This test requires a connected and properly driver-configured FTDI DMX interface.

    controller = None
    try:
        print("Initializing DMXController (will attempt to open FTDI device)...")
        # Using context manager for robust cleanup
        with DMXController(auto_start_thread=False, update_rate_hz=20) as controller: # Slower rate for testing
            if not controller.dmx_sender:
                print("DMXController could not initialize DMXSender. Check connection/drivers. Exiting test.")
                exit(1)

            print("Starting DMX output...")
            controller.start_dmx_output()
            if not controller.is_running:
                print("Failed to start DMX output thread. Exiting test.")
                exit(1)

            print("\nTesting channel setting:")
            print("Setting channel 1 to 128, channel 2 to 255.")
            controller.set_channel(1, 128)
            controller.set_channel(2, 255)

            time.sleep(0.5)

            val1 = controller.get_channel(1)
            val2 = controller.get_channel(2)
            print(f"Read back: Channel 1 = {val1}, Channel 2 = {val2}")
            assert val1 == 128, f"Expected Ch1=128, got {val1}"
            assert val2 == 255, f"Expected Ch2=255, got {val2}"

            print("\nTesting set_channels:")
            controller.set_channels(10, [50, 100, 150])
            time.sleep(0.5)
            print(f"Read back: Ch10={controller.get_channel(10)}, Ch11={controller.get_channel(11)}, Ch12={controller.get_channel(12)}")
            assert controller.get_channel(10) == 50
            assert controller.get_channel(11) == 100
            assert controller.get_channel(12) == 150

            print("\nPerforming a ~2-second chase on channels 1-3 (slower for visibility)...")
            # Chase for about 2 seconds. Each step 0.3s. 3 steps per cycle. Cycle = 0.9s. ~2 cycles.
            for cycle in range(2):
                for i in range(1, 4): # Channels 1, 2, 3
                    if not controller.is_running: break

                    # Set previous channel in chase to 0
                    prev_ch_in_chase = i - 1 if i > 1 else 3
                    controller.set_channel(prev_ch_in_chase, 0)

                    controller.set_channel(i, 200)
                    # print(f"Chase: Cycle {cycle+1}, Channel {i} set to 200")
                    time.sleep(0.3)
                if not controller.is_running: break

            if controller.is_running:
                print("\nSending blackout...")
                controller.blackout()
                time.sleep(0.5)

            print("\nTest sequence finished.")
            # Controller will be closed automatically by __exit__

    except FtdiError as e:
        print(f"FTDI specific error in test script: {e}")
        print("Please ensure your FTDI DMX device is connected and drivers (e.g. libusb via Zadig on Windows) are correctly installed.")
    except Exception as e:
        print(f"An error occurred in the test script: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # If not using context manager, explicit close would be here:
        # if controller:
        #     print("Closing DMXController in finally block...")
        #     controller.close()
        print("DMX Controller Test Script Finished.")
