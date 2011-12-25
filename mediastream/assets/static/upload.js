$(document).ready(function() {
    // allow multiple files to be uploaded
    $('#id_file').prop('multiple', true);

    // upload progress bar
    // see https://github.com/drogus/jquery-upload-progress
    $('form#upform').uploadProgress({
        /* scripts locations for safari */
        jqueryPath: jqpath,
        uploadProgressPath: uppath,
        start: function () {
            $("#upload_form").hide();
            filename = $("#id_file").val().split(/[\/\\]/).pop();
            $("#progress_status").html("Uploading " + filename + "...");
            $("#progress_container").show();
        },
        uploading: function(upload) {
            if (upload.percents == 100) {
                window.clearTimeout(this.timer);
                $("#progress_filename").html("Processing " + filename + "...");
            } else {
                $("#progress_filename").html("Uploading " + filename + ": " + upload.percents + "%");
            };
        },
        progressBar: "#progress_indicator",
        progressUrl: "/assets/upload/progress",
        interval: 2000
    });
});
