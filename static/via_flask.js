// overwrite default ImageMetaData function to add db_id to it.
function ImageMetadata(fileref, filename, size) {
  this.filename = filename;
  this.size = size;
  this.fileref = fileref; // image url or local file ref.
  this.regions = [];
  this.file_attributes = {}; // image attributes
  this.base64_img_data = ''; // image data stored as base 64
  this.db_id = -1; // db id
}

// overwrite to lose popup
function show_localStorage_recovery_options() {}

// this function is used by the main via script to determine loading of extra function
function _via_load_submodules() {
  remove_via_data_from_localStorage();
  var params = get_get_request_url_parameters();
  if (typeof params.ids !== 'undefined') {
    var image_ids_db = params.ids.split('_')
    load_images_from_database(image_ids_db);
  }
}

// links to homepage when clicking on button
function redirect_to_homepage() {
  var location = window.location;
  var full = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '');
  window.location.href = full;
}

// links to database when clicking on button
function redirect_to_database() {
  var location = window.location;
  var full = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '');
  full += '/admin/annotatedimage'
  window.location.href = full;
}

// get the request params of the URL
function get_get_request_url_parameters() {
  var prmstr = window.location.search.substr(1);
  return prmstr != null && prmstr != "" ? transform_to_association_array(prmstr) : {};
}

// transform the request params to an object
function transform_to_association_array(params_string) {
  var params = {};
  var param_list = params_string.split("&");
  for (var i = 0; i < param_list.length; i++) {
    var key_value_list = param_list[i].split("=");
    params[key_value_list[0]] = key_value_list[1];
  }
  return params;
}

// loads the image_ids specified in the url from the database
function load_images_from_database(image_ids_db) {
  img_loading_spinbar(true);
  for (var i = 0; i < image_ids_db.length; i++) {
    var image_id_db = image_ids_db[i]
    retrieve_image_metadata_and_location_from_db(image_id_db)
    _via_image_index = 0;
  }
  toggle_img_list()
  img_loading_spinbar(false);
}

// first retrieve the image metadata
function retrieve_image_metadata_and_location_from_db(image_db_id) {
  var oReq = new XMLHttpRequest();
  var oData = new FormData();
  oData.append('image_id', image_db_id)
  oReq.open("POST", "/retrieve_classified_img_from_db", true);
  oReq.onload = function(oEvent) {
    if (oReq.status == 200) {
      // then do another AJAX inside the ajax, where all the stuff happens
      download_img_and_update(JSON.parse(oReq.response))
    } else {
      show_message("Error " + oReq.status + " occurred when trying to upload your file")
    }
  }
  oReq.send(oData);
}

// use the image metadata to download the image, and then add the image program wide
function download_img_and_update(img_metadata) {
  var oReq = new XMLHttpRequest();

  // first request the binary image data
  oReq.open("GET", img_metadata.file_location, true);
  oReq.responseType = "blob";
  oReq.onload = function(oEvent) {
    if (oReq.status == 200) {

      var img_id = _via_get_image_id(img_metadata.filename, img_metadata.filesize);
      imd = new ImageMetadata('', img_metadata.filename, img_metadata.filesize);

      // retrieve the file from the response
      var y = new File([oReq.response], img_metadata.filename)
      imd.fileref = y
      imd.db_id = img_metadata.img_db_id

      // update global values
      _via_img_metadata[img_id] = imd;
      _via_image_id_list.push(img_id);
      _via_img_count += 1;
      _via_reload_img_table = true;

      var info = {
        fileref: "",
        size: img_metadata.filesize,
        filename: img_metadata.filename,
        base64_img_data: "",
        file_attributes: img_metadata.file_attributes,
        regions: img_metadata.regions
      }

      var x = {};
      x[img_id] = info
      var regioninfo = JSON.stringify(x)

      import_annotations_from_json(regioninfo)
      show_message('image with id ' + img_metadata.img_db_id + ' was loaded from db')
    } else {
      show_message(oReq.response)
    }
  }
  oReq.send();
}

// converts a img to a file
function data_URI_to_blob(data_uri) {
  var byte_string;
  if (data_uri.split(',')[0].indexOf('base64') >= 0)
    byte_string = atob(data_uri.split(',')[1]);
  else
    byte_string = unescape(data_uri.split(',')[1]);

  var mime_string = data_uri.split(',')[0].split(':')[1].split(';')[0];

  var int_array = new Uint8Array(byte_string.length);
  for (var i = 0; i < byte_string.length; i++) {
    int_array[i] = byte_string.charCodeAt(i);
  }

  return new Blob([int_array], {
    type: mime_string
  });
}

// sends and image and its regions to the database using a file form and formdata
function send_classified_image_to_backend() {
  var blob = data_URI_to_blob(_via_current_image.src);
  var filename = _via_img_metadata[_via_image_id].filename

  var oData = new FormData();

  // only add the image when it's not stored in the db yet
  if(_via_img_metadata[_via_image_id].db_id == -1){
    oData.append("image_file", blob, filename);
  }
  oData.append('image_metadata_and_regions', JSON.stringify(_via_img_metadata[_via_image_id]))
  oData.append('db_id', _via_img_metadata[_via_image_id].db_id)

  var oReq = new XMLHttpRequest();
  oReq.open("POST", "/add_classified_img_to_db", true);
  oReq.onload = function(oEvent) {
    if (oReq.status == 200) {
      data = JSON.parse(oReq.response)
      _via_img_metadata[_via_image_id].db_id = data.db_id
      show_message('image with id ' + data.db_id + 'was added to db')
    } else {
      show_message("Error " + oReq.status + " occurred when trying to upload your file because " + oReq.response)
    }
  };
  oReq.send(oData);
}
