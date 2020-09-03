import enum
from bottle.ext import sqlalchemy as bottle_sqlalchemy
from json import dumps
from sqlalchemy import (
        create_engine,
        Column,
        Enum,
        Integer,
        Binary,
        Sequence,
        String,
    )
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = create_engine('sqlite:///:memory:', echo=False)


def tuple_to_json(t):
    ret = {}
    for (key, val) in t._asdict().items():
        if isinstance(val, bytes):
            val = val.decode()
        ret[key] = val
    return dumps(ret)

class AudioFile(Base):
    __tablename__ = 'audio_file'
    name         = Column(String, nullable=False, primary_key=True)

    # This data is compressed using ZLib
    data         = Column(Binary, nullable=False)
    size         = Column(Integer, nullable=False)

    # {
    # This is my best guess of the most important metrics.
    runtime_sec  = Column(Integer, nullable=False)
    channels     = Column(Integer, nullable=False)
    bitwidth     = Column(Integer, nullable=False)
    sample_rate  = Column(Integer, nullable=False)
    # }

    # {
    # Everything else is dumped into here in free-form fields for
    # later use.
    wave_header  = Column(String, nullable=False)
    wave_format  = Column(String, nullable=False)
    # }

    @staticmethod
    def FromWaveParser(name, parser):
        af = AudioFile()
        af.name = name
        af.data = parser.parse()
        af.size = len(af.data)
        af.channels = parser.format.channels
        af.bitwidth = parser.format.bits_per_sample
        af.sample_rate = parser.format.samples_per_second
        af.runtime_sec = (8 * parser.header.chunk_size) \
                       / (af.channels * af.bitwidth * af.sample_rate)

        af.wave_header = tuple_to_json(parser.header)
        af.wave_format = tuple_to_json(parser.format)

        return af

    @property
    def info(self):
        fields = [
            'name',
            'size',
            'runtime_sec',
            'channels',
            'bitwidth',
            'sample_rate',
        ]

        ret = {}
        for col in fields:
            ret[col] = getattr(self, col)
        return ret


def init_plugin():
    plugin = bottle_sqlalchemy.Plugin(
            engine,
            Base.metadata,
            keyword='db',
            create=True,
            commit=True,
            use_kwargs=False)
    return plugin

