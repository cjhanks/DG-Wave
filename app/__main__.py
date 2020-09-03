from uuid import uuid4
import zlib
import flask
from flask import (
        Flask,
        request,
        jsonify,
        )
import db
from parser import (
        WaveException,
        WaveParser,
        )

# {
# Install the app
app = Flask('deepgram')
#app.install(db.init_plugin())
# }


# ----
class HttpError(Exception):
    def __init__(self, http_code, message=None):
        Exception.__init__(self)
        self.status_code = http_code
        self.message = {'error': message or ''}


@app.errorhandler(HttpError)
def handle_invalid_usage(error):
    response = jsonify(error.message)
    response.status_code = error.status_code
    return response

# ----


@app.route('/post', methods=['POST'])
@db.inject_db
def post_wave(cnct):
    """
    This allows a user to post files to the serve one of two ways, either
    through the upload of multiple form-data files OR via a standard post
    body upload.
    """
    files = []

    if request.mimetype == 'multipart/form-data':
        for _, file in request.files.items():
            files.append((file.filename, file))
    else:
        files.append(('%s.wav' % uuid4(), request.stream))

    response = []
    for (name, fp) in files:
        parser = WaveParser(fp)
        try:
            audio_file = db.AudioFile.FromWaveParser(name, parser)
            cnct.add(audio_file)
        except WaveException as err:
            raise HttpError(406, str(err)) from None
        except Exception as err:
            print(err)
            raise HttpError(500) from None

        response.append(audio_file.info)

    cnct.commit()
    return {'files': response}


@app.route('/download', methods=['GET'])
@db.inject_db
def get_wave(cnct):
    name = request.args.get('name')
    if name is None:
        raise HttpError(400, 'No name requested')

    try:
        item = cnct.query(db.AudioFile).filter(db.AudioFile.name==name).one()
    except Exception:
        raise HttpError(404, 'No such file found')

    return zlib.decompress(item.data)


# --
class QueryOptions:
    Options = {}

    @staticmethod
    def Compile():
        for klass in QueryOptions.__subclasses__():
            QueryOptions.Options[klass.Name] = klass

class QueryMaxDuration(QueryOptions):
    Name = 'maxduration'

    def __init__(self, value):
        self.value = float(value)

    def augment(self, query):
        return query.filter(db.AudioFile.runtime_sec < self.value)

class QueryMaxDuration(QueryOptions):
    Name = 'minduration'

    def __init__(self, value):
        self.value = float(value)

    def augment(self, query):
        return query.filter(db.AudioFile.runtime_sec > self.value)

QueryOptions.Compile()

@app.route('/list')
@db.inject_db
def list_wave(cnct):
    query = cnct.query(db.AudioFile)

    for (key, val) in request.args.items():
        klass = QueryOptions.Options.get(key)
        # Not sure if it should be ignored, but ok.
        if klass is None:
            continue
        else:
            query = klass(val).augment(query)

    results = []
    for item in query.all():
        results.append(item.info)

    return {'file': results}

@app.route('/info')
@db.inject_db
def info_wave(cnct):
    name = request.args.get('name')
    if name is None:
        raise HttpError(400, 'No name requested')

    try:
        item = cnct.query(db.AudioFile).filter(db.AudioFile.name==name).one()
    except Exception:
        raise HttpError(404, 'No such file found')

    return item.info

app.run()
