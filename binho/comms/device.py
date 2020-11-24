# import usb
import time

import threading
import queue
import signal
import sys
import serial
import os
import enum
import collections
import serial

from ..errors import DeviceNotFoundError

from .manager import binhoDeviceManager
from .comms import binhoComms
from .drivers.core import binhoCoreDriver
from .drivers.i2c import binhoI2CDriver
from .drivers.spi import binhoSPIDriver
from .drivers.io import binhoIODriver
from .drivers.onewire import binho1WireDriver


class binhoAPI(object):

    HANDLED_BOARD_IDS = []
    USB_VID_PID = "04D8"

    @classmethod
    def populate_default_identifiers(cls, device_identifiers, find_all=False):
        """
        Populate a dictionary of default identifiers-- which can
        be overridden or extended by arguments to the function.
        device_identifiers -- any user-specified identifers; will override
            the default identifiers in the event of a conflit
        """

        # By default, accept any device with the default vendor/product IDs.
        identifiers = {
            "idVendor": cls.BOARD_VENDOR_ID,
            "idProduct": cls.BOARD_PRODUCT_ID,
            "find_all": find_all,
        }
        identifiers.update(device_identifiers)

        return identifiers

    def __init__(self, **device_identifiers):

        self.serialPort = device_identifiers["port"]
        self.comms = binhoComms(device_identifiers["port"])

        self.apis = collections.OrderedDict()

        self.apis.core = binhoCoreDriver(self.comms)
        self.apis.i2c = binhoI2CDriver(self.comms)
        self.apis.spi = binhoSPIDriver(self.comms)
        self.apis.oneWire = binho1WireDriver(self.comms)
        self.apis.io = collections.OrderedDict()
        self.apis.swi = None
        self.apis.uart = None

        self.handler = None
        self.manager = None
        self.interrupts = None
        self._stopper = None
        self._txdQueue = None
        self._rxdQueue = None
        self._intQueue = None
        self._debug = os.getenv("BINHO_NOVA_DEBUG")

        self._inBootloader = False

        # By default, accept any device with the default vendor/product IDs.
        self.identifiers = self.populate_default_identifiers(device_identifiers)

        # For convenience, allow serial_number=None to be equivalent to not
        # providing a serial number: a board with any serial number will be
        # accepted.
        if (
            "serial_number" in self.identifiers
            and self.identifiers["serial_number"] is None
        ):
            del self.identifiers["serial_number"]

        # TODO: replace this with a comms_string
        # Create our backend connection to the device.
        # self.comms = CommsBackend.from_device_uri(**self.identifiers)

        # Get an object that allows easy access to each of our APIs.
        # self.apis = self.comms.generate_api_object()

        # TODO: optionally use the core API to discover other APIs

        # Final sanity check: if we don't handle this board ID, bail out!
        # if self.HANDLED_BOARD_IDS and (self.board_id() not in self.HANDLED_BOARD_IDS):
        #    raise DeviceNotFoundError()

    # Destructor
    def __del__(self):

        self.comms.close()

    # Public functions
    @classmethod
    def autodetect(cls, board_identifiers):
        # Iterate over each subclass of binhoHostAdapter until we find a board
        # that accepts the given board ID.

        for subclass in cls.__subclasses__():
            if subclass.accepts_connected_device(board_identifiers):

                # Create an instance of the device to return,
                # and ensure that device has fully populated comms APIs.
                board = subclass(**board_identifiers)

                board.initialize_apis()

                return board

        # If we couldn't find a board, raise an error.
        raise DeviceNotFoundError()

    @classmethod
    def autodetect_all(cls, device_identifiers):
        """
        Attempts to create a new instance of the Binho host adapter subclass
        most applicable for each board present on the system-- similar to the
        behavior of autodetect.
        Accepts the same arguments as pyusb's usb.find() method, allowing narrowing
        to a more specific Binho Host Adapter by e.g. serial number.
        Returns a list of Binho Host Adapters, which may be empty if none are found.
        """

        devices = []

        # Iterate over each subclass of Binho host adapters until we find a board
        # that accepts the given board ID.
        for subclass in cls.__subclasses__():

            # Get objects for all devices accepted by the given subclass.

            subclass_devices = subclass.all_accepted_devices(**device_identifiers)

            # FIXME: It's possible that two classes may choose to both advertise support
            # for the same device, in which case we'd wind up with duplicats here. We could
            # try to filter out duplicates using e.g. USB bus/device, but that assumes
            # things are USB connected.
            devices.extend(subclass_devices)

        # Ensure each device has its comms objects fully populated.
        for device in devices:
            device.initialize_apis()

        # Return the list of all subclasses.
        return devices

    @classmethod
    def all_accepted_devices(cls, **device_identifiers):
        """
        Returns a list of all devices supported by the given class. This should be
        overridden if the device connects via anything other that USB.
        Accepts the same arguments as pyusb's usb.find() method, allowing narrowing
        to a more specific Binho host adapter by e.g. serial number.
        """

        devices = []

        # Grab the list of all devices that we theoretically could use.
        # FIXME: use the comms backend for this!
        # identifiers = cls.populate_default_identifiers(device_identifiers, find_all=True)
        manager = binhoDeviceManager()
        availablePorts = manager.listAvailablePorts()
        identifiers = {}

        # Iterate over all of the connected devices, and filter out the devices
        # that this class doesn't connect.
        for port in availablePorts:

            # We need to be specific about which device in particular we're
            # grabbing when we query things-- or we'll get the first acceptable
            # device every time. The trick here is to populate enough information
            # into the identifier to uniquely identify the device. The address
            # should do, as pyusb is only touching enmerated devices.
            identifiers["port"] = port
            identifiers["find_all"] = False

            # If we support the relevant device _instance_, and it to our list.
            if cls.accepts_connected_device(identifiers):
                devices.append(cls(**identifiers))

        return devices

    @classmethod
    def accepts_connected_device(cls, device_identifiers):
        """
        Returns true iff the provided class is appropriate for handling a connected
        Binho host adapter.
        Accepts the same arguments as pyusb's usb.find() method, allowing narrowing
        to a more specific Binho host adapter by e.g. serial number.
        """

        manager = binhoDeviceManager()

        if "deviceID" in device_identifiers and device_identifiers["deviceID"]:

            port = manager.getPortByDeviceID(device_identifiers["deviceID"])
            device_identifiers["port"] = port

        elif "index" in device_identifiers:

            ports = manager.listAvailablePorts()
            if len(ports) <= device_identifiers["index"]:
                raise DeviceNotFoundError
            device_identifiers["port"] = ports[device_identifiers["index"]]

        try:

            usb_hwid = manager.getUSBVIDPIDByPort(device_identifiers["port"])

        except DeviceNotFoundError:
            return False

        # Accept only Binho host adapters whose board IDs are handled by this
        # class. This is mostly used by subclasses, which should override
        # HANDLED_BOARD_IDS.
        if usb_hwid:
            return cls.USB_VID_PID in usb_hwid
        else:
            return False

    @property
    def deviceID(self):
        """Reads the board ID number for the device."""
        return self.apis.core.deviceID

    @property
    def commPort(self):
        return self.serialPort

    def usb_info(self, port):
        usb_info = binhoDeviceManager.getUSBVIDPIDByPort(port)
        return usb_info

    @property
    def productName(self):
        """Returns the human-readable product-name for the device."""
        return self.PRODUCT_NAME

    @property
    def firmwareVersion(self):
        """Reads the board's firmware version."""
        return self.apis.core.firmwareVersion

    @property
    def hardwareVersion(self):
        return self.apis.core.hardwareVersion

    @property
    def commandVersion(self):
        return self.apis.core.commandVersion

    @property
    def inBootloaderMode(self):
        return self._inBootloader

    def initialize_apis(self):
        """Hook-point for sub-boards to initialize their APIs after
        we have comms up and running and auto-enumeration is complete.
        """

        # Open up the commport.
        self.comms.start()

        try:
            self.deviceID
            self._inBootloader = False
            return True
        except BaseException:
            self._inBootloader = True
            return False

    def addIOPinAPI(self, name, ioPinNumber):
        self.apis.io[ioPinNumber] = binhoIODriver(self.comms, ioPinNumber)

    def supports_api(self, class_name):
        """ Returns true iff the board supports the given API class. """
        return class_name in self.apis

    def version_warnings(self):
        """Returns any warning messages relevant to the device's firmware version.
        Can be used to warn the user when an upgrade is required.
        Returns a string with any warnings, or None  if no warnings apply.
        """
        return None

    def close(self):
        self.comms.close()


def _to_hex_string(byte_array):
    """Convert a byte array to a hex string."""

    hex_generator = ("{:02x}".format(x) for x in byte_array)
    return "".join(hex_generator)
