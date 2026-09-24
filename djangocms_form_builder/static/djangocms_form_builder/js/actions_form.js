document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    for (const element of document.querySelectorAll('fieldset.action-auto-hide input[type="checkbox"][name="form_actions"]')) {
        const getByClass = (className) => (document.getElementsByClassName('c' + className) || [undefined])[0];
        const target = getByClass(element.value);
        const setActionState = (fieldset, selected) => {
            fieldset.classList.toggle("action-hide", !selected);
            for (const field of fieldset.querySelectorAll('[data-action-required="true"]')) {
                field.required = selected;
            }
        };

        if (target) {
            setActionState(target, element.checked);
            if (!target.querySelector('.form-row:not(.hidden)')) {
                target.classList.add("empty");
            }
            element.addEventListener('change', function (event) {
                const fieldset = getByClass(event.target.value);
                if (fieldset) {
                    setActionState(fieldset, event.target.checked);
                }
            });
        }
    }
});
