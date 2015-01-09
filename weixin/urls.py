from django.conf.urls import patterns, url
from views import Weixin

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    url(r'^(\w+)/$', Weixin.as_view(), name='weixin_entry'),
)
