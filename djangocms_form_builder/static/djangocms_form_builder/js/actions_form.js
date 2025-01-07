$(function () {
    'use strict';
    $('fieldset.action-auto-hide input[type="checkbox"][name="form_actions"]').each(function (index, element) {
        const target = $('.' + $(element).attr("value"));
        if (element.checked) {
            target.removeClass("action-hide");
        }
        if (!target.find('.form-row:not(.hidden)').length) {
            target.addClass("empty");
        }
        $(element).on("change", function (event) {
            var element = event.target;
            if (element.checked) {
                $("." + $(element).val()).removeClass("action-hide");
            } else {
                $("." + $(element).val()).addClass("action-hide");
            }
        });
    });
});
