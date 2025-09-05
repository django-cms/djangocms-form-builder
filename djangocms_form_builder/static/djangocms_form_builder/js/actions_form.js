document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    for (const element of document.querySelectorAll('fieldset.action-auto-hide input[type="checkbox"][name="form_actions"]')) {
        const getByClass = (className) => (document.getElementsByClassName('c' + className) || [undefined])[0];
        const target = getByClass(element.value);

        if (target) {
            if (element.checked) {
                target.classList.remove("action-hide");
            }
            if (!target.querySelector('.form-row:not(.hidden)')) {
                target.classList.add("empty");
            }
            element.addEventListener('change', function (event) {
                if (event.target.checked) {
                    getByClass(event.target.value)?.classList.remove("action-hide");
                } else {
                    getByClass(event.target.value)?.classList.add("action-hide");
                }
            });
        }
    }
});
