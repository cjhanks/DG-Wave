import enum
import struct
from collections import namedtuple
import zlib


class WaveException(RuntimeError):
    pass

WaveHeader = \
    namedtuple('WaveHeader', ['chunk_id', 'chunk_size', 'wave_id'])

WaveFormat = \
    namedtuple('WaveFormat', [
        'format_tag',
        'channels',
        'samples_per_second',
        'average_bytes_per_second',
        'block_align',
        'bits_per_sample',
        'extension_size',
        'valid_bits_per_sample',
        'channel_mask',
        'subformat',
    ])

class WaveParser:
    Header = '4sI4s'
    Format = ['H', 'H', 'I', 'I', 'H', 'H', 'H', 'H', 'I16s']

    def __init__(self, fp):
        self.__fp = fp
        self.__read_size = 0
        self.header = None
        self.format = None
        self.__compressor = zlib.compressobj()
        self.__data = b''

    def read(self, size):
        data = self.__fp.read(size)
        self.__read_size += len(data)
        self.__data += self.__compressor.compress(data)

        return data

    def parse(self):
        self.header = self.__parse_header()

        while True:
            data = self.read(4)

            # At end of file.
            if len(data) == 0:
                break

            # Some WAVE files tested had case issues.
            data = data.upper()
            if len(data) != 4:
                raise WaveException('Truncated WAVE file')

            # The specification for WAVE is as diverse as the day is long,
            # not even Python implements a full featured WAVE parser, so
            # I won't here, either.  We will only consider the important
            # parts.
            if   data == b'FMT ':
                self.format = self.__parse_format()
            elif data == b'DATA':
                self.__parse_data()
            else:
                # Read until the end.
                self.read(None)

        if self.header is None or self.format is None:
            raise WaveException('Invalid WAVE file')

        return self.__get_data()

    def __get_data(self):
        ret = self.__data + self.__compressor.flush()
        del self.__data
        return ret

    def __parse_header(self):
        size = struct.calcsize(WaveParser.Header)
        data = self.read(size)
        if len(data) != size:
            raise WaveException('Truncated header')

        return WaveHeader(*struct.unpack(WaveParser.Header, data))

    def __parse_format(self):
        # The first 4 bytes in the stream will indicate how large the format
        # section is.  First parse that, and then determine which parts of
        # the format header are null.
        data = self.read(4)
        size = struct.unpack('I', data)[0]

        for i in range(len(self.Format)):
            pack_string = ''.join(self.Format[:i])
            if struct.calcsize(pack_string) == size:
                break
        else:
            raise WaveException('Unknown WAVE format type')

        # Now unpack the elements by parsing them.
        size = struct.calcsize(pack_string)
        data = self.read(size)
        elements = struct.unpack(pack_string, data)

        # The `WaveFormat` structure is larger than the minimum, so we pack the
        # unfilled sections with `None`.
        elements += (None,) * (len(WaveFormat._fields) - len(elements))

        return WaveFormat(*elements)

    def __parse_data(self):
        data = self.read(4)
        size = struct.unpack('I', data)[0]
        self.data_size = size

        # Consume the data.
        data = self.read(size)
        if size != len(data):
            raise WaveException('Truncated WAVE file')


if __name__ == '__main__':
    #n = 'wav16.wav'
    n = 'example1.wav'
    #n = 'wav8.wav'
    with open(n, 'rb') as fp:
        parser = WaveParser(fp)
        data = parser.parse()
        print(parser.header)
        print(parser.format)
        print(parser.data_size)

        print(len(data))
