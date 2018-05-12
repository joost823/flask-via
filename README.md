# Manual Image Annotator/Classifier with a Flask backend
This is a Flask application, which uses [VGG Image Annotator](http://www.robots.ox.ac.uk/~vgg/) in order
to manually mark regions on images, which can later be used as input regions for image
classification/machine learning projects. The problem with running VIA as standalone program
in the browser is that was not an easy way to organise your data. Here, this app comes into play.
It saves the images and the connected regions in a database, which can easily
be edited, reloaded, and deleted, both one by one and in batches.

To make it run locally:
```
git clone https://github.com/joost823/flask-via
cd flask-via
pip install -r requirements.txt
```

on windows:
`set FLASK_APP=app.py`

on unix:
`export FLASK_APP=app.py`

```
flask run
```

# VGG Image Annotator

VGG Image Annotator (VIA) is an open source project developed at the
[Visual Geometry Group](http://www.robots.ox.ac.uk/~vgg/) and released under
the BSD-2 clause license. This work is supported by EPSRC programme grant
Seebibyte: Visual Search for the Era of Big Data ([EP/M013774/1](http://www.seebibyte.org/index.html)).
Visit the [VGG software page](http://www.robots.ox.ac.uk/~vgg/software/via/) for more details.


## Features:
  * based solely on HTML, CSS and Javascript (no external javascript libraries)
  * can be used off-line (full application in a single html file of size &lt; 200KB)
  * requires nothing more than a modern web browser (tested on Firefox, Chrome and Safari)
  * supported region shapes: rectangle, circle, ellipse, polygon and point
  * import/export of region data in csv and json file format


## Downloads
 * VGG Image Annotator (VIA)
   * [via-1.0.5.zip](http://www.robots.ox.ac.uk/~vgg/software/via/downloads/via-1.0.5.zip) : includes the VIA application (&lt; 200KB) and its demo
   * [via-src-1.0.5.zip](http://www.robots.ox.ac.uk/~vgg/software/via/downloads/via-src-1.0.5.zip) : source code and [code documentation](https://gitlab.com/vgg/via/blob/master/CodeDoc.md)
   * [via.html](http://www.robots.ox.ac.uk/~vgg/software/via/via.html) : online version of VIA application
   * [via_demo.html](http://www.robots.ox.ac.uk/~vgg/software/via/via_demo.html) : live online demo (with preloadd images and regions)


## Docs
 * Getting Started : this can be accessed by pressing F1 key in the VIA application.
 * [VIA Software page @ VGG](http://www.robots.ox.ac.uk/~vgg/software/via/)
 * [VIA Wikipedia page](https://en.wikipedia.org/wiki/VGG_Image_Annotator)


## License
VIA is an open source project released under the
[BSD-2 clause license](https://gitlab.com/vgg/via/blob/master/LICENSE).

## Author
[Abhishek Dutta](mailto:adutta@robots.ox.ac.uk)  
Aug. 31, 2016
