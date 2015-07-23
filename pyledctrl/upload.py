"""Bytecode uploader for PyLedCtrl."""

from __future__ import print_function

import re
import sys


class BytecodeUploader(object):
    """Bytecode uploader for PyLedCtrl."""

    def __init__(self, port):
        """\
        :param port: the serial port to upload the bytecode to.
        :type port: groundctrl.serial_port.SerialPort
        """
        self.port = port

    def log(self, message):
        """Prints a log message."""
        print(message, file=sys.stderr)

    def upload(self, bytecode):
        """Uploads the given bytecode to the LED controller.

        :param bytecode: the bytecode to upload as a raw Python bytes object
        :type bytecode: bytes
        """
        length = len(bytecode)

        try:
            fd = self.port.fdspawn()

            self.log("Waiting for device to finish booting...")
            if self._wait_for_response() != 0:
                return

            self.log("Sending bytecode...")
            fd.send(b"U")
            fd.send(chr((length & 0xFF00) >> 16))
            fd.send(chr(length & 0xFF))
            fd.send(bytecode)
            fd.send("\n")
            response = self._wait_for_response()
            if response != 0:
                self.log("Bytecode upload failed.")
            else:
                self.log("Bytecode uploaded successfully.")
            return response
        finally:
            self.port.close()

    def upload_file(self, filename):
        """Uploads the bytecode from the given file to the LED controller.

        :param filename: the name of the file containing the bytecode to upload
        :type filename: str
        """
        return self.upload(open(filename, "rb").read())

    def _wait_for_response(self):
        """Waits for the next response on the associated serial port.

        :return: an error code or zero if the serial port returned a message
             indicating success.
        """
        fd = self.port.fdspawn()
        index = fd.expect(["\\+OK\r?\n", "-E(.*)\r?\n"])
        if index:
            self.log("Device returned error code {0}.".format(fd.match.group(1)))
            return int(fd.match.group(1))
        else:
            return 0
