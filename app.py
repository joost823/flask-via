import os
import json
import base64
import datetime
import mimetypes

from jinja2 import Markup
from flask_admin import Admin
from flask_wtf import FlaskForm
from sqlalchemy import select, func
from flask_admin.actions import action
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for
from wtforms import StringField, validators
from flask_admin.contrib.sqla import ModelView
from wtforms.validators import ValidationError
from sqlalchemy.ext.hybrid import hybrid_property
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask import Flask, request, url_for, render_template, jsonify, send_from_directory, redirect


def generate_via_template():
    navbar_first_item_str = '<li><a onclick="show_home_panel()" title="Home">Home</a></li>'
    insert_js_here_str = '//<!--AUTO_INSERT_VIA_JS_HERE-->'
    with open('templates/index.html') as fin, open('templates/via_flask.html', 'w') as fout:
        for line in fin:
            if navbar_first_item_str in line:
                indentation = line.split(navbar_first_item_str)[0]
                to_be_added = ['<li><a onclick="show_home_panel()" title="Via Home">Via Home</a></li>',
                               '<li><a onclick="redirect_to_homepage()" title="Website Home">Website Home</a></li>',
                               '<li><a onclick="redirect_to_database()" title="DB">DB</a></li>',
                               '<li><a onclick="send_classified_image_to_backend()" title="Save">Save</a></li>']
                fout.write(indentation + ('\n' + indentation).join(to_be_added) + '\n')
            elif insert_js_here_str in line:
                indentation = line.split(insert_js_here_str)[0]
                to_be_added = ['</script>',
                               '<script type="text/javascript" src="{{url_for("static", filename="via.js")}}"></script>',
                               '<script type="text/javascript" src="{{url_for("static", filename="via_flask.js")}}"></script>',
                               '<script>']
                fout.write(indentation + ('\n' + indentation).join(to_be_added) + '\n')
            else:
                fout.write(line)


generate_via_template()


app = Flask(__name__)
app.config['via_folder'] = 'images'
app.config['WTF_CSRF_ENABLED'] = False
app.config['SECRET_KEY'] = 'you-should-change-this'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///via.sqlite'
db = SQLAlchemy(app)
admin = Admin(app)


class ManuallyClassifiedPicture(db.Model):
    __tablename__ = 'manuallyclassifiedpicture'
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String)
    filesize = db.Column(db.Integer)
    fname_when_uploaded = db.Column(db.String)
    file_attributes = db.Column(db.String)
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    regions = db.relationship("PictureRegion", backref="picture", lazy='dynamic', cascade="save-update, merge, delete")

    @hybrid_property
    def number_of_regions(self):
        return len(self.regions.all())

    @number_of_regions.expression
    def number_of_regions(cls):
        return db.select([db.func.count(PictureRegion.id)]).where(PictureRegion.manual_picture_id == cls.id).label("number_of_regions")


class PictureRegion(db.Model):
    __tablename__ = 'pictureregion'
    id = db.Column(db.Integer, primary_key=True)
    manual_picture_id = db.Column(db.Integer, db.ForeignKey('manuallyclassifiedpicture.id'))
    shape_attributes = db.Column(db.String)
    region_attributes = db.Column(db.String)
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)


@listens_for(ManuallyClassifiedPicture, 'after_delete')
def delManualImg(mapper, connection, target):
    if target.fname:
        os.remove(app.config['via_folder'] + '/' + target.fname)


db.create_all()


class AddManuallyClassifiedPictureForm(FlaskForm):
    image_metadata_and_regions = StringField('Regions', [validators.required()])
    image_file = FileField('image', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])

    def validate_image_metadata_and_regions(form, field):
        try:
            data = json.loads(field.data)
        except json.decoder.JSONDecodeError as e:
            raise ValidationError(f'field not jsonifyable, details = {e}')

        for param in ['filename', 'file_attributes', 'db_id', 'regions']:
            if param not in data:
                raise ValidationError(f'param {param} not found in json')
        for region in data['regions']:
            for param in ['shape_attributes', 'region_attributes']:
                if param not in region:
                    raise ValidationError(f'param {param} not found in region')
        form.regions = data['regions']
        form.db_id = data['db_id']
        form.fname = data['filename']
        form.file_attributes = data['file_attributes']


class ManuallyClassifiedPictureView(ModelView):
    column_list = ('id', 'fname', 'img', 'created_date', 'edit regions', 'number_of_regions')
    column_sortable_list = ['id', 'number_of_regions', 'fname', 'created_date']
    can_create = False
    column_display_pk = True

    @action('edit_using_via', 'Edit Using VIA', 'Edit selected images?')
    def action_edit_using_via(self, ids):
        id_string = '_'.join(ids)
        url = url_for('via_template', ids=id_string)
        return redirect(url)

    def _edit(view, context, model, name):
        url = url_for('via_template', ids=model.id)
        return Markup(f'<a href="{url}">edit regions</a>')

    def _list_img(view, context, model, name):
        if not model.fname:
            return ''
        image_loc = url_for('send_file', folder=app.config['via_folder'] + '/', filename=model.fname)
        url = url_for('via_template', ids=model.id)
        return Markup(f'<a href="{url}"><img src="{image_loc}" height="42" width="42"></a>')

    column_formatters = {
        'img': _list_img,
        'edit regions': _edit}


admin.add_view(ManuallyClassifiedPictureView(ManuallyClassifiedPicture, db.session))
admin.add_view(ModelView(PictureRegion, db.session))


@app.route('/', methods=['GET'])
def index():
    return '<a href="/via_template">VIA</a><br><a href="/admin/manuallyclassifiedpicture">admin</a>'


@app.route('/via_template', methods=['GET'])
def via_template():
    return render_template('via_flask.html')


@app.route('/send_file/<path:folder>/<path:filename>')
def send_file(folder, filename):
    if folder in [app.config['via_folder'] + '/']:
        return send_from_directory(folder, filename)
    else:
        return 'no', 406


@app.route('/add_classified_img_to_db', methods=['POST'])
def add_classified_img_to_db():
    form = AddManuallyClassifiedPictureForm()
    if form.validate_on_submit():
        if form.db_id != -1:
            pic = ManuallyClassifiedPicture.query.get_or_404(form.db_id)
            for region in pic.regions:
                db.session.delete(region)
        else:
            pic = ManuallyClassifiedPicture()
            db.session.add(pic)

        db.session.commit()

        pic.fname_when_uploaded = form.image_file.data.filename
        fname_old_no_ext, ext = os.path.splitext(form.image_file.data.filename)
        pic.fname = str(pic.id) + ext

        form.image_file.data.save(app.config['via_folder'] + '/' + pic.fname)

        pic.filesize = os.path.getsize(app.config['via_folder'] + '/' + pic.fname)
        pic.file_attributes = json.dumps(form.file_attributes)

        for region in form.regions:
            pc = PictureRegion()
            pc.shape_attributes = json.dumps(region['shape_attributes'])
            pc.region_attributes = json.dumps(region['region_attributes'])
            pc.manual_picture_id = pic.id
            db.session.add(pc)
        db.session.commit()

        return jsonify({'db_id': pic.id})

    else:
        return str(form.errors), 400


@app.route('/retrieve_classified_img_from_db', methods=['POST'])
def retrieve_classified_img_from_db():
    if request.method == 'POST':
        image_id = request.form['image_id']
        image = ManuallyClassifiedPicture.query.get_or_404(image_id)
        regions = []
        for region in image.regions:
            regiondict = {}
            regiondict['shape_attributes'] = json.loads(region.shape_attributes)
            regiondict['region_attributes'] = json.loads(region.region_attributes)
            regions.append(regiondict)

        with open(app.config['via_folder'] + '/' + image.fname, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        image_info = {}
        image_info['fileref'] = ''
        image_info['size'] = len(encoded_string)
        image_info['filename'] = image.fname
        image_info['file_attributes'] = json.loads(image.file_attributes)
        image_info['regions'] = regions
        mimetype = mimetypes.MimeTypes().guess_type(image.fname)[0]

        return jsonify({'image_raw': 'data:' + mimetype + ';base64,' + encoded_string,
                        'img_info': image_info,
                        'img_db_id': image.id,
                        'filesize': image.filesize})
