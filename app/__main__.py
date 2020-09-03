import flask
from flask import (
        Flask,
        request,
        jsonify,
        )
import db
from uuid import uuid4
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
def post_wave():
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
        except WaveException as err:
            raise HttpError(406, str(err)) from None
        except Exception as err:
            print(err)
            raise HttpError(500) from None

        response.append(audio_file.info)

    return {'files': response}

#@app.route('/download',)
#def get_wave(db):
#    pass
#
#@app.get('/list')
#def list_wave(db):
#    pass
#
#@app.get('/info')
#def info_wave(db):
#    pass


app.run()
