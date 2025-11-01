// Get the error message from the script tag that loaded this script
function getErrorMessage() {
    const currentScript = document.currentScript || document.querySelector('script[src*="ajax_form.js"]');
    if (currentScript && currentScript.dataset.errorMsg) {
        return currentScript.dataset.errorMsg;
    }
    return "Network connection or server error. Please try again later. We apologize for the inconvenience.";
}

function djangocms_form_builder_form(form) {
    function feedback(node, data) {
        if (data.result === 'success') {
            node.outerHTML = data.content;
            node.style.transition='';
            node.style.opacity = 0;
            node.style.transition='opacity 0.3s';
            node.style.opacity = 1;
        } else if (data.result === 'result') {
            for (let invalid of node.getElementsByClassName('all-invalid')) {
                invalid.classList.add('d-none');
                let li = invalid.getElementsByTagName('li');
                while (li !== undefined && li.length > 0) {
                    li[0].remove();
                }
            }
            for (let group of node.getElementsByClassName('.form-group')) {
                group.classList.add('has-feedback has-success is-valid');
                group.classList.remove('has-error is-invalid');
                let invalid = group.getElementsByClassName('invalid-feedback');
                while (invalid !== undefined && invalid.length > 0) {
                    invalid[0].remove();
                }
            }
            if (node.dataset.results) {
                let target = document.getElementById(node.dataset.results);
                const range = document.createRange();
                const fragment = range.createContextualFragment(data.content);
                target.appendChild(fragment);
            }
        } else if (data.result === 'invalid form') {
            for (let invalid of node.getElementsByClassName('all-invalid')) {
                invalid.classList.add('d-none');
                let li = invalid.getElementsByTagName('li');
                while (li !== undefined && li.length > 0) {
                    li[0].remove();
                }
            }
            let invalid = node.getElementsByClassName('invalid-feedback');
            while (invalid !== undefined && invalid.length > 0) {
                invalid[0].remove();
            }
            for (const [key, value] of Object.entries(data.field_errors)) {
                for (const err of value) {
                    if (key.substring(0,7) !== "__all__") {
                        let msg = document.createElement('template');

                        msg.innerHTML = "<div class='invalid-feedback'><strong></strong></div>";
                        msg.content.querySelector('strong').innerText = err;
                        document.getElementById(key).after(msg.content);
                    } else {
                        let msg = document.createElement('template');
                        msg.innerHTML = "<li></li>";
                        msg.content.querySelector('li').innerText = err;
                        for (let invalid of node.getElementsByClassName('all-invalid')) {
                            invalid.classList.remove('d-none');
                            let ul = invalid.getElementsByTagName("ul");
                            if (ul.length > 0) {
                                ul[0].appendChild(msg.content);
                            }
                        }
                    }
                }
            }
            // make invalid fields visible in collapsed sections
            for(let collapse of node.getElementsByClassName('collapse')) {
                if (collapse.getElementsByClassName('invalid-feedback').length > 0) {
                    collapse.classList.add('show');
                }
            }
            node.classList.add('was-validated');
        } else if (data.result === 'error') {
            alert(data.errors[0]);
        }
        if ('redirect' in data) {
            if (data.redirect !== '' && data.redirect !== 'result') {
                window.location.href = data.redirect;
            } else if (data.redirect !== '') {
                window.location.reload();
            }
        }
    }

    function submitEvent(event) {
        event.preventDefault();
        post_ajax(form);
    }

    function post_ajax(node) {
        fetch(node.getAttribute('action'),{
            method: 'POST',
            body: new URLSearchParams(new FormData(node)),
            }
        ).then(function (response) {
            return response.json();
            }
        ).then(function (data) {
            feedback(node, data);
        }).catch(function (json) {
            console.error(json);
            alert(getErrorMessage());
        });
    }

    let recaptcha = form.getElementsByClassName('g-recaptcha');
    if (recaptcha.length === 1) {
        let submitButton = form.querySelector('input[type="submit"]');
        submitButton.setAttribute("disabled", "");
        let checkExist = setInterval(function () {
            if (window.hasOwnProperty("recaptcha_loaded")) {
                clearInterval(checkExist);
                submitButton.removeAttribute("disabled");
                let gid = grecaptcha.render(recaptcha[0], {
                    "callback": function (token) {
                        form.getElementsByClassName("g-recaptcha-response")[0].value = token;
                        post_ajax(form);
                        grecaptcha.reset(gid);
                    },
                });
                if(!form.dataset.submitEvent) {
                    form.dataset.submitEvent = true;
                    form.addEventListener('submit', function (event) {
                        event.preventDefault();
                        console.log("recaptcha submit")
                        grecaptcha.execute(gid);
                    });
                }
            }
        }, 100);
    } else {
        if(!form.dataset.submitEvent) {
            form.dataset.submitEvent = true;
            form.addEventListener('submit', function (event) {
                event.preventDefault();
                post_ajax(form);
            });
        }
    }
}

function reCaptchaOnLoadCallback() {
    window.recaptcha_loaded = true;
};

(function () {
    function initForms() {
        for (let form of document.getElementsByClassName('djangocms-form-builder-ajax-form')) {
            djangocms_form_builder_form(form);
        }
    }
    window.addEventListener('load', initForms);
})();
