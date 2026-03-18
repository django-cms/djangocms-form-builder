from django.contrib import admin
from django.urls import include, path
from django_altcha import AltchaChallengeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("altcha/challenge/", AltchaChallengeView.as_view(), name="altcha_challenge"),
    path("", include("cms.urls")),
]
