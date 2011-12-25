(function($) {
    $(document).ready(function($) {
        // Select a bunch of ticky boxes on the Change Asset Queue page.
        window.queuer_select_old_deletes = true;
        $('#select_old_deletes_trigger').click(function () {
            $('tbody > tr:contains("Has been played") > td.delete > input[type="checkbox"]').attr('checked', window.queuer_select_old_deletes);
            if (window.queuer_select_old_deletes) {
                $(this).text("Unselect all");
                window.queuer_select_old_deletes = false;
            } else {
                $(this).text("Select all");
                window.queuer_select_old_deletes = true;
            }
        });
    });
})(django.jQuery);
