(function($) {
    // collapse filter list on change forms 
    $(document).ready(function($) {
        $("#changelist-filter ul").hide();
        $("#changelist-filter h3").css('cursor', 'pointer');
        $("#changelist-filter h3").click(function() {
          $(this).next("ul").slideToggle(600);
        });
    });
})(django.jQuery);
