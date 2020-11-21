class binhoSPIDriver:
    def __init__(self, usb, spiIndex=0):

        self.usb = usb
        self.spiIndex = 0

    @property
    def clockFrequency(self):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " CLK ?")
        result = self.usb._readResponse()

        if not result.startswith("-SPI" + str(self.spiIndex) + " CLK"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-SPI'
                + str(self.spiIndex)
                + ' CLK"'
            )
        else:
            return int(result[10:])

    @clockFrequency.setter
    def clockFrequency(self, clock):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " CLK " + str(clock))
        result = self.usb._readResponse()

        if not result.startswith("-OK"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-OK"'
            )
        else:
            return True

    @property
    def bitOrder(self):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " ORDER ?")
        result = self.usb._readResponse()

        if not result.startswith("-SPI" + str(self.spiIndex) + " ORDER"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-SPI'
                + str(self.spiIndex)
                + ' ORDER"'
            )
        else:
            return result[12:]

    @bitOrder.setter
    def bitOrder(self, order):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " ORDER " + order)
        result = self.usb._readResponse()

        if not result.startswith("-OK"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-OK"'
            )
        else:
            return True

    @property
    def mode(self):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " MODE ?")
        result = self.usb._readResponse()

        if not result.startswith("-SPI" + str(self.spiIndex) + " MODE"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-SPI'
                + str(self.spiIndex)
                + ' MODE"'
            )
        else:
            return int(result[11:])

    @mode.setter
    def mode(self, mode):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " MODE " + str(mode))
        result = self.usb._readResponse()

        if not result.startswith("-OK"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-OK"'
            )
        else:
            return True

    @property
    def bitsPerTransfer(self):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " TXBITS ?")
        result = self.usb._readResponse()

        if not result.startswith("-SPI" + str(self.spiIndex) + " TXBITS"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-SPI'
                + str(self.spiIndex)
                + ' TXBITS"'
            )
        else:
            return int(result[13:])

    @bitsPerTransfer.setter
    def bitsPerTransfer(self, bits):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " TXBITS " + str(bits))
        result = self.usb._readResponse()

        if not result.startswith("-OK"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-OK"'
            )
        else:
            return True

    def begin(self):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " BEGIN")
        result = self.usb._readResponse()

        if not result.startswith("-OK"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-OK"'
            )
        else:
            return True

    def transfer(self, data):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " TXRX " + str(data))
        result = self.usb._readResponse()

        if not result.startswith("-SPI" + str(self.spiIndex) + " RXD"):
            raise RuntimeError(
                f'Error Binho responded with {result}, not the expected "-SPI'
                + str(self.spiIndex)
                + ' RXD"'
            )
        else:
            return bytearray.fromhex(result[9:])

    def writeToReadFrom(self, write, read, numBytes, data):

        dataPacket = ""
        writeOnlyFlag = "0"

        if write:
            if numBytes > 0:
                for i in range(numBytes):
                    dataPacket += "{:02x}".format(data[i])
            else:
                dataPacket = "0"
        else:
            # read only, keep writing the same value
            for i in range(numBytes):
                dataPacket += "{:02x}".format(data)

        if not read:
            writeOnlyFlag = "1"

        self.usb._sendCommand(
            "SPI"
            + str(self.spiIndex)
            + " WHR "
            + writeOnlyFlag
            + " "
            + str(numBytes)
            + " "
            + dataPacket
        )

        result = self.usb._readResponse()

        if not read:
            if not result.startswith("-OK"):
                raise RuntimeError(
                    f'Error Binho responded with {result}, not the expected "-OK"'
                )
            else:
                return bytearray()
        else:
            if not result.startswith("-SPI0 RXD "):
                raise RuntimeError(
                    f'Error Binho responded with {result}, not the expected "-SPI0 RXD ..."'
                )
            else:
                return bytearray.fromhex(result[9:])

    def end(self, suppressError=False):

        self.usb._sendCommand("SPI" + str(self.spiIndex) + " END")
        result = self.usb._readResponse()

        if not result.startswith("-OK"):
            if not suppressError:
                raise RuntimeError(
                    f'Error Binho responded with {result}, not the expected "-OK"'
                )
        else:
            return True