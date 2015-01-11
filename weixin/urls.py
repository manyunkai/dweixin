from django.conf.urls import patterns, url
from django.contrib import admin

from .views import Weixin

admin.autodiscover()


urlpatterns = patterns('',
    url(r'^(\w+)/$', Weixin.as_view(), name='weixin_entry'),
)
