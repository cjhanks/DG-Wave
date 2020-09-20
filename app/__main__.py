from io import BytesIO
from uuid import uuid4
import zlib
import flask
from flask import (
        Flask,
        request,
        jsonify,
        Response,
        )
import db
from parser import (
        WaveException,
        WaveParser,
        )
from sqlalchemy.sql.expression import func, select

# {
# Install the app
app = Flask('deepgram')
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

@app.route('/')
def form():
    content = '''
<html>
<body>
<h1>DG</h1>
<hr>
</br>
<form action="post" method="post" enctype="multipart/form-data">
  <input type="file" name="file_upload"></input>
  </br>
  <input type="submit" value="Upload Wave File" name="submit">
  </br>
</form>
<hr>
<form action="list" method="get" enctype="multipart/form-data">
  MinDuration: <input type="text" name="minduration"></input>
  </br>
  <input type="submit" value="List files" name="submit">
  </br>
</form>
<hr>
<form action="info" method="get" enctype="multipart/form-data">
  Name: <input type="text" name="name"></input>
  </br>
  <input type="submit" value="Info" name="submit">
  </br>
</form>
<hr>
<form action="download" method="get" enctype="multipart/form-data">
  Name: <input type="text" name="name"></input>
  </br>
  <input type="submit" value="Download" name="submit">
  </br>
</form>
</body>


</html>
'''
    return content

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

    return Response(
            zlib.decompress(item.data),
            mimetype='audio/wave',
            headers={'Content-Disposition':
                        'attachment; filename=%s' % item.name})


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
        if value:
            self.value = float(value)
        else:
            self.value = float('inf')

    def augment(self, query):
        return query.filter(db.AudioFile.runtime_sec < self.value)

class QueryMaxDuration(QueryOptions):
    Name = 'minduration'

    def __init__(self, value):
        if value:
            self.value = float(value)
        else:
            self.value = 0

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

@app.route('/random')
@db.inject_db
def random_segment(cnct):
    audio_file = cnct.query(db.AudioFile).order_by(func.random()).first()
    audio_data = BytesIO(zlib.decompress(audio_file.data))
    audio_parsed = WaveParser(audio_data)
    print(audio_parsed.header)
    print(audio_parsed.format)
    print(audio_parsed.pcm_data)

    pass

app.run()
