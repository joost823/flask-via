import os
import json
import base64
import datetime

from jinja2 import Markup
from flask_wtf import FlaskForm
from sqlalchemy import select, func
from flask_admin.menu import MenuLink
from flask_admin import Admin, expose
from flask_admin.actions import action
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for
from wtforms import StringField, validators
from flask_admin.contrib.sqla import ModelView
from wtforms.validators import ValidationError
from sqlalchemy.ext.hybrid import hybrid_property
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask import Flask, request, url_for, render_template, jsonify, send_from_directory, redirect


app = Flask(__name__)
app.config['via_folder'] = 'images'
app.config['WTF_CSRF_ENABLED'] = False
app.config['SECRET_KEY'] = 'you-should-change-this'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///via.sqlite'
db = SQLAlchemy(app)
admin = Admin(app)


class AnnotatedImage(db.Model):
    __tablename__ = 'annotatedimage'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String)
    filesize = db.Column(db.Integer)
    filename_when_uploaded = db.Column(db.String)
    file_attributes = db.Column(db.String)
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    regions = db.relationship("ImageRegion", backref="image", lazy='dynamic', cascade="save-update, merge, delete")

    @hybrid_property
    def number_of_regions(self):
        return len(self.regions.all())

    @number_of_regions.expression
    def number_of_regions(cls):
        return db.select([db.func.count(ImageRegion.id)]).where(ImageRegion.image_id == cls.id).label("number_of_regions")


class ImageRegion(db.Model):
    __tablename__ = 'imageregion'
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('annotatedimage.id'))
    shape_attributes = db.Column(db.String)
    region_attributes = db.Column(db.String)
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)


@listens_for(AnnotatedImage, 'after_delete')
def delManualImg(mapper, connection, target):
    if target.filename:
        os.remove(app.config['via_folder'] + '/' + target.filename)


db.create_all()


class AddAnnotatedImageForm(FlaskForm):
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
        form.filename = data['filename']
        form.file_attributes = data['file_attributes']


class AnnotatedImageView(ModelView):
    column_list = ('id', 'filename', 'filesize', 'img', 'created_date', 'edit regions', 'number_of_regions')
    column_sortable_list = ['id', 'filesize', 'number_of_regions', 'filename', 'created_date']
    column_display_pk = True

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        return redirect(url_for('via_template'))

    @action('edit_using_via', 'Edit Using VIA', 'Edit selected images?')
    def action_edit_using_via(self, ids):
        id_string = '_'.join(ids)
        url = url_for('via_template', ids=id_string)
        return redirect(url)

    def _edit(view, context, model, name):
        url = url_for('via_template', ids=model.id)
        return Markup(f'<a href="{url}">edit regions</a>')

    def _list_img(view, context, model, name):
        if not model.filename:
            return ''
        image_loc = url_for('send_file', folder=app.config['via_folder'], filename=model.filename)
        url = url_for('via_template', ids=model.id)
        return Markup(f'<a href="{url}"><img src="{image_loc}" height="42" width="42"></a>')

    column_formatters = {
        'img': _list_img,
        'edit regions': _edit}


admin.add_view(AnnotatedImageView(AnnotatedImage, db.session))
admin.add_view(ModelView(ImageRegion, db.session))
admin.add_link(MenuLink(name='Homepage', url='/'))
admin.add_link(MenuLink(name='VIA', url='/via_template'))


@app.route('/', methods=['GET'])
def index():
    return '<a href="/via_template">VIA</a><br><a href="/admin/annotatedimage">admin</a>'


@app.route('/via_template', methods=['GET'])
def via_template():
    return render_template('via_flask.html')


@app.route('/send_file/<path:folder>/<path:filename>')
def send_file(folder, filename):
    if '/' in filename or folder not in [app.config['via_folder']]:
        return 'not allowed', 400
    return send_from_directory(folder, filename)


@app.route('/add_classified_img_to_db', methods=['POST'])
def add_classified_img_to_db():
    form = AddAnnotatedImageForm()
    if form.validate_on_submit():
        if form.db_id != -1:
            pic = AnnotatedImage.query.get_or_404(form.db_id)
            for region in pic.regions:
                db.session.delete(region)
        else:
            pic = AnnotatedImage()
            db.session.add(pic)

        db.session.commit()

        pic.filename_when_uploaded = form.image_file.data.filename
        filename_old_no_ext, ext = os.path.splitext(form.image_file.data.filename)
        pic.filename = str(pic.id) + ext

        form.image_file.data.save(app.config['via_folder'] + '/' + pic.filename)

        pic.filesize = os.path.getsize(app.config['via_folder'] + '/' + pic.filename)
        pic.file_attributes = json.dumps(form.file_attributes)

        for region in form.regions:
            ir = ImageRegion()
            ir.shape_attributes = json.dumps(region['shape_attributes'])
            ir.region_attributes = json.dumps(region['region_attributes'])
            ir.image_id = pic.id
            db.session.add(ir)
        db.session.commit()

        return jsonify({'db_id': pic.id})

    else:
        return str(form.errors), 400


@app.route('/retrieve_classified_img_from_db', methods=['POST'])
def retrieve_classified_img_from_db():
    image_id = request.form['image_id']
    image = AnnotatedImage.query.get_or_404(image_id)
    regions = []
    for region in image.regions:
        regiondict = {}
        regiondict['shape_attributes'] = json.loads(region.shape_attributes)
        regiondict['region_attributes'] = json.loads(region.region_attributes)
        regions.append(regiondict)

    return jsonify({'filename_when_uploaded': image.filename_when_uploaded,
                    'filename': image.filename,
                    'file_attributes': json.loads(image.file_attributes),
                    'regions': regions,
                    'filesize': image.filesize,
                    'img_db_id': image.id,
                    'file_location': url_for('send_file',
                                             folder=app.config['via_folder'],
                                             filename=image.filename)})


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


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
