const formsetSelector = "django-formset[data-djangocms-form-builder-formset]";
const submitSelector = "[data-djangocms-form-builder-submit]";

async function submitFormset(formset) {
    if (formset.dataset.submitting) {
        return;
    }

    const error = formset.querySelector("[data-djangocms-form-builder-error]");
    const buttons = Array.from(formset.querySelectorAll(submitSelector));
    const disabled = buttons.map((button) => button.disabled);
    const showError = (status) => {
        error.textContent = status === 403
            ? formset.dataset.csrfErrorMessage : formset.dataset.errorMessage;
        error.hidden = false;
        error.focus();
    };
    error.hidden = true;
    formset.dataset.submitting = "true";
    formset.setAttribute("aria-busy", "true");
    buttons.forEach((button) => { button.disabled = true; });
    try {
        // django-formset reports browser constraints and 422 field errors itself.
        const response = await formset.submit();
        if (!response) {
            // Its runtime also returns undefined after a failed fetch. Avoid
            // showing a server error when browser validation prevented submission.
            if (Array.from(formset.querySelectorAll("form")).every((form) => form.checkValidity())) {
                showError();
            }
            return;
        }
        if (response.status === 422) {
            return;
        }
        if (response.status !== 200) {
            showError(response.status);
            return;
        }

        const result = await response.json();
        if (result.content) {
            const range = document.createRange();
            formset.replaceWith(range.createContextualFragment(result.content));
        } else if (result.success_url) {
            window.location.assign(result.success_url);
        }
    } catch {
        showError();
    } finally {
        delete formset.dataset.submitting;
        formset.removeAttribute("aria-busy");
        buttons.forEach((button, index) => { button.disabled = disabled[index]; });
    }
}

// Keep django-formset's validation on button activation, including the browser's
// implicit button click when Enter is pressed in a form control.
document.addEventListener("click", (event) => {
    const button = event.target instanceof Element && event.target.closest(submitSelector);
    const formset = button && button.closest(formsetSelector);
    if (formset) {
        event.preventDefault();
        void submitFormset(formset);
    }
});

// Also support requestSubmit() and submits with no implicit button activation.
document.addEventListener("submit", (event) => {
    const formset = event.target instanceof HTMLFormElement && event.target.closest(formsetSelector);
    if (formset) {
        event.preventDefault();
        void submitFormset(formset);
    }
});
