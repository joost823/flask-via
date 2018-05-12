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

function data_URI_to_blob(data_uri) {
  // convert base64/URLEncoded data component to raw binary data held in a string
  var byte_string;
  if (data_uri.split(',')[0].indexOf('base64') >= 0)
    byte_string = atob(data_uri.split(',')[1]);
  else
    byte_string = unescape(data_uri.split(',')[1]);

  // separate out the mime component
  var mime_string = data_uri.split(',')[0].split(':')[1].split(';')[0];

  // write the bytes of the string to a typed array
  var ia = new Uint8Array(byte_string.length);
  for (var i = 0; i < byte_string.length; i++) {
    ia[i] = byte_string.charCodeAt(i);
  }

  return new Blob([ia], {
    type: mime_string
  });
}

function redirect_to_homepage() {
  var location = window.location;
  var full = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '');
  window.location.href = full;
}

function redirect_to_database() {
  var location = window.location;
  var full = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '');
  full += '/admin/manuallyclassifiedpicture'
  window.location.href = full;
}

function get_search_parameters() {
  var prmstr = window.location.search.substr(1);
  return prmstr != null && prmstr != "" ? transform_to_association_array(prmstr) : {};
}

function transform_to_association_array(prmstr) {
  var params = {};
  var prmarr = prmstr.split("&");
  for (var i = 0; i < prmarr.length; i++) {
    var tmparr = prmarr[i].split("=");
    params[tmparr[0]] = tmparr[1];
  }
  return params;
}

function send_classified_image_to_backend() {
  var blob = data_URI_to_blob(_via_current_image.src);
  var fname = _via_img_metadata[_via_image_id].filename

  var oData = new FormData();
  oData.append("image_file", blob, fname);
  oData.append('image_metadata_and_regions', JSON.stringify(_via_img_metadata[_via_image_id]))

  var oReq = new XMLHttpRequest();
  oReq.open("POST", "/add_classified_img_to_db", true);
  console.log(_via_img_metadata[_via_image_id]);
  oReq.onload = function(oEvent) {
    if (oReq.status == 200) {
      data = JSON.parse(oReq.response)
      _via_img_metadata[_via_image_id].db_id = data.db_id
      console.log(data.db_id)
      show_message('image with id ' + data.db_id + 'was added to db')
    } else {
      show_message("Error " + oReq.status + " occurred when trying to upload your file because " + oReq.response)
    }
  };
  oReq.send(oData);
}

function _via_load_submodules() {
  update_navbar()
  var params = get_search_parameters();
  if (typeof params.ids !== 'undefined') {
    var image_ids_db = params.ids.split('_')
    load_images_from_database(image_ids_db);
  }
}

function update_navbar(){
  var x = document.getElementsByClassName("navbar");
  console.log(x[0].firstChild)
}


function load_images_from_database(image_ids_db) {
  for (var i = 0; i < image_ids_db.length; i++) {
    var image_id_db = image_ids_db[i]
    send_image_request(image_id_db)
    _via_image_index = 0;
  }
  toggle_img_list()
}

function send_image_request(image_db_id) {
  var oReq = new XMLHttpRequest();
  var oData = new FormData();
  oData.append('image_id', image_db_id)
  oReq.open("POST", "/retrieve_classified_img_from_db", true);
  oReq.onload = function(oEvent) {
    if (oReq.status == 200) {
      var data = JSON.parse(oReq.response)
      var fileinfo = data.img_info
      var filename = fileinfo.filename
      var rawimg = data.image_raw
      var size = data.filesize
      var img_id_j = _via_get_image_id(filename, size);

      imd = new ImageMetadata('', filename, size);
      imd.db_id = data.img_db_id
      imd.base64_img_data = rawimg

      _via_img_metadata[img_id_j] = imd;
      _via_image_id_list.push(img_id_j);
      _via_img_count += 1;
      _via_reload_img_table = true;

      var x = {};
      x[img_id_j] = fileinfo
      var regioninfo = JSON.stringify(x)

      import_annotations_from_json(regioninfo)
      show_message('image with id ' + data.img_db_id + ' was loaded from db')
    } else {
      show_message("Error " + oReq.status + " occurred when trying to upload your file")
    }
  }
  oReq.send(oData);
}
