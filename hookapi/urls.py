from django.conf.urls import patterns, include, url
from rest_framework import routers
from hookapi.quickstart import views

from django.contrib import admin
admin.autodiscover()


router = routers.DefaultRouter()
router.register(r'hooks', views.HookView,base_name='hooks')

urlpatterns = patterns('',
    url(r'^', include(router.urls)),
    url(r'^admin/', include(admin.site.urls)),
)
