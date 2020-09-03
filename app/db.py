import enum
from functools import wraps
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
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm.session import (
        sessionmaker,
    )
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def tuple_to_json(t):
    ret = {}
    for (key, val) in t._asdict().items():
        if isinstance(val, bytes):
            val = val.decode()
        ret[key] = val
    return dumps(ret)


def inject_db(func):
    @wraps(func)
    def __func__(*args, **kwargs):
        return func(*args, cnct=Session(), **kwargs)
    return __func__

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

engine = create_engine(
        'sqlite:///:memory:',
        echo=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, autoflush=True)
