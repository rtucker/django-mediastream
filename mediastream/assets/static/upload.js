$(document).ready(function() {
    // allow multiple files to be uploaded
    $('#id_file').prop('multiple', true);

    // upload progress bar
    // see https://github.com/drogus/jquery-upload-progress
    $('form').uploadProgress({
        /* scripts locations for safari */
        jqueryPath: jqpath,
        uploadProgressPath: uppath,
        /* function called each time bar is updated */
        uploading: function(upload) {$('#percents').html(upload.percents+'%');},
        /* selector or element that will be updated */
        progressBar: "#progressbar",
        /* progress reports url */
        progressUrl: "/progress",
        /* how often will bar be updated */
        interval: 2000
    });
});
