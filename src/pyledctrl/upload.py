"""Bytecode uploader for PyLedCtrl."""

from __future__ import print_function

import sys


class BytecodeUploader:
    """Bytecode uploader for PyLedCtrl."""

    def __init__(self, port):
        """\
        :param port: the serial port to upload the bytecode to.
        :type port: groundctrl.serial_port.SerialPort
        """
        self.port = port
        self.length = 0

    def log(self, message):
        """Prints a log message."""
        print(message, file=sys.stderr)

    def upload(self, bytecode):
        """Uploads the given bytecode to the LED controller.

        :param bytecode: the bytecode to upload as a raw Python bytes object
        :type bytecode: bytes
        """
        length = self.length = len(bytecode)

        try:
            fd = self.port.fdspawn()
            fd = self.port.fdspawn()

            self.log("Waiting for device to finish booting...")
            while True:
                response = self._wait_for_response(fd)
                if not response:
                    self.log("Device failed to boot.")
                    return False
                elif response.message == "READY":
                    break

            self.log("Querying maximum bytecode size...")
            fd.send(b"c\n")
            response = self._wait_for_response(fd)
            if not response.successful:
                self.log("Failed to query maximum bytecode size.")
                return False

            max_bytecode_size = int(response.message)
            if max_bytecode_size < length:
                self.log(
                    "Cannot upload bytecode; maximum allowed size is {0} bytes "
                    "but we tried to upload {1} bytes.".format(
                        max_bytecode_size, length
                    )
                )
                return False

            self.log("Sending bytecode...")
            fd.send(b"U")
            fd.send(chr((length >> 8) & 0xFF))
            fd.send(chr(length & 0xFF))
            fd.send(bytecode)
            fd.send("\n")

            response = self._wait_for_response(fd)
            if response.successful:
                self.log("Bytecode uploaded successfully.")
            else:
                self.log("Bytecode upload failed.")
            return response.successful
        finally:
            self.port.close()
            self.length = None

    def upload_file(self, filename):
        """Uploads the bytecode from the given file to the LED controller.

        :param filename: the name of the file containing the bytecode to upload
        :type filename: str
        """
        return self.upload(open(filename, "rb").read())

    def _wait_for_response(self, fd):
        """Waits for the next response on the associated serial port.

        :return: an error code or zero if the serial port returned a message
             indicating success.
        """
        while True:
            index = fd.expect(
                ["\\+([^\r\n]*)\r?\n", "-E([^\r\n]*)\r?\n", ":([^\r\n]*)\r?\n"]
            )
            if index == 2:
                try:
                    bytes_uploaded = int(fd.match.group(1))
                    sys.stderr.write(
                        "{0:.2f}%\r".format(100.0 * bytes_uploaded / self.length)
                    )
                except Exception:
                    pass
            elif index == 1:
                self.log("Device returned error code {0}.".format(fd.match.group(1)))
                return Response.failure(fd.match.group(1))
            else:
                return Response.success(fd.match.group(1))


class Response:
    """Represents a response from the Arduino."""

    @classmethod
    def failure(cls, message):
        return cls(message, successful=False)

    @classmethod
    def success(cls, message):
        return cls(message, successful=True)

    def __init__(self, message, successful):
        self.message = message
        self.successful = bool(successful)

    def __nonzero__(self):
        return self.successful
