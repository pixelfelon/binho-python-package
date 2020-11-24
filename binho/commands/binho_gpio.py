import sys
import time
import argparse
import statistics
from binho.utils import log_silent, log_verbose, binho_error_hander
from binho.errors import DeviceNotFoundError


def main():
    from binho.utils import binhoArgumentParser

    # Set up a simple argument parser.
    parser = binhoArgumentParser(
        description="utility for reading from Binho host adapter's ADC"
    )
    parser.add_argument(
        "-m",
        "--mode",
        dest="mode",
        type=str,
        default="DIN",
        choices=["DIN", "DOUT"],
        help="Set the mode of the IO pin",
    )
    parser.add_argument(
        "-n", "--iopin", default=0, help="Provide the IO pin to use for this operation"
    )
    parser.add_argument("-o", "--output", default=None, help="Set the output value")

    args = parser.parse_args()

    log_function = log_verbose if args.verbose else log_silent

    try:
        log_function("Trying to find a Binho host adapter...")
        device = parser.find_specified_device()

        if device.inBootloaderMode:
            print(
                "{} found on {}, but it cannot be used now because it's in DFU mode".format(
                    device.productName, device.commPort
                )
            )
            sys.exit(errno.ENODEV)
        else:
            log_function(
                "{} found on {}. (Device ID: {})".format(
                    device.productName, device.commPort, device.deviceID
                )
            )

    except DeviceNotFoundError:
        if args.serial:
            print(
                "No Binho host adapter found matching Device ID '{}'.".format(
                    args.serial
                ),
                file=sys.stderr,
            )
        else:
            print("No Binho host adapter found!", file=sys.stderr)
        sys.exit(errno.ENODEV)

    # if we fail before here, no connection to the device was opened yet.
    # however, if we fail after this point, we need to make sure we don't
    # leave the serial port open.

    try:

        device.operationMode = "IO"

        pin = {}

        if args.iopin:
            if args.iopin.isnumeric():
                pinStr = "IO" + str(args.iopin)
            else:
                pinStr = args.iopin.upper()
        else:
            pinStr = "IO0"

        # get the desired pin
        pin = device.gpio.getPin(pinStr)

        # set the pin mode
        if args.output:
            pin.mode = "DOUT"

            if args.output.isnumeric():

                if int(args.output) == 0:
                    pin.value = 0
                elif int(args.output) == 1:
                    pin.value = 1
                else:
                    raise ValueError(
                        "Output can only be set to 0 or 1, not {}".format(args.output)
                    )

                log_function(
                    "Configured {} as a digital output = {} ".format(
                        pinStr, int(args.output)
                    )
                )

            elif args.output.upper() == "HIGH":
                pin.value = 1
                log_function(
                    "Configured {} as a digital output and drove the signal {} ".format(
                        pinStr, args.output.upper()
                    )
                )
            elif args.output.upper() == "LOW":
                pin.value = 0
                log_function(
                    "Configured {} as a digital output and drove the signal {} ".format(
                        pinStr, args.output.upper()
                    )
                )
            else:
                raise ValueError(
                    "Output can only be set to LOW or HIGH, not {}".format(args.output)
                )

        else:

            pin.mode = "DIN"
            value = pin.value
            if value == 0:
                log_function("{} is 0 (LOW)".format(pinStr))
            elif value == 1:
                log_function("{} is 1 (HIGH)".format(pinStr))

        # close the connection to the host adapter
        device.close()

    except Exception:
        # Catch any exception that was raised and display it
        binho_error_hander()

        # close the connection to the host adapter
        device.close()


if __name__ == "__main__":
    main()
