document.addEventListener("click", async (event) => {
    if (!(event.target instanceof Element)) {
        return;
    }

    const button = event.target.closest("[data-djangocms-form-builder-submit]");
    const formset = button?.closest("django-formset[data-djangocms-form-builder-formset]");
    if (!formset || formset.dataset.submitting) {
        return;
    }

    event.preventDefault();
    formset.dataset.submitting = "true";
    button.disabled = true;
    try {
        // django-formset validates and reports field errors before returning a response.
        const response = await formset.submit();
        if (!response || response.status !== 200) {
            return;
        }

        const result = await response.json();
        if (result.content) {
            const range = document.createRange();
            formset.replaceWith(range.createContextualFragment(result.content));
        } else if (result.success_url) {
            window.location.assign(result.success_url);
        }
    } finally {
        delete formset.dataset.submitting;
        button.disabled = false;
    }
});
