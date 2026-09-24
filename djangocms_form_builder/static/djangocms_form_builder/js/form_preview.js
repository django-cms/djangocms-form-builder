// A form shown in the form editor - in edit and in preview mode - is for
// looking at, not for submitting: it is tried out on a page showing it.
// A script of its own rather than an inline onsubmit handler, which a
// Content Security Policy would block.
document.addEventListener('submit', function (event) {
    'use strict';

    if (event.target.classList.contains('djangocms-form-builder-preview')) {
        event.preventDefault();
    }
}, true);
