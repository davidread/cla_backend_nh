from django.conf.urls import patterns, url
from django.conf import settings
from moj_irat.views import HealthcheckView
from . import views


urlpatterns = patterns(
    "",
    url(r"^$", views.status),
    url(r"^status.json$", views.smoketests),
    url(r"^ping.json$", views.PingJsonView.as_view(**settings.PING_JSON_KEYS), name="ping_json"),
    url(r"^healthcheck.json$", HealthcheckView.as_view(), name="healthcheck_json"),
)
