from . import legacy  # noqa F401
from .ajax_plugins import FormPlugin
from .form_plugins import (
    BooleanFieldPlugin,
    CaptchaPlugin,
    CharFieldPlugin,
    ChoicePlugin,
    DateFieldPlugin,
    DateTimeFieldPlugin,
    DecimalFieldPlugin,
    EmailFieldPlugin,
    IntegerFieldPlugin,
    SelectPlugin,
    SubmitPlugin,
    TextareaPlugin,
    TimeFieldPlugin,
    URLFieldPlugin,
)

__all__ = [
    "FormPlugin",
    "BooleanFieldPlugin",
    "CaptchaPlugin",
    "CharFieldPlugin",
    "ChoicePlugin",
    "DateFieldPlugin",
    "DateTimeFieldPlugin",
    "DecimalFieldPlugin",
    "EmailFieldPlugin",
    "IntegerFieldPlugin",
    "SelectPlugin",
    "SubmitPlugin",
    "TextareaPlugin",
    "TimeFieldPlugin",
    "URLFieldPlugin",
]
