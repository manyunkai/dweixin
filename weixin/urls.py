from django.conf.urls import patterns, url
from django.contrib import admin

from .views import Weixin, UserLocationFetching

admin.autodiscover()


urlpatterns = patterns(
    '',
    url(r'^location/fetch/$', UserLocationFetching.as_view(), name='weixin_fetch_user_location'),
    url(r'^(\w+)/$', Weixin.as_view(), name='weixin_entry'),
)
