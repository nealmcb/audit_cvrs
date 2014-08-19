from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import TemplateView, ListView
import django_databrowse

from audit_cvrs.models import *

admin.autodiscover()

django_databrowse.site.register(CVR)

cvr_dict = {
    'queryset': CVR.objects.all(),
}

urlpatterns = patterns('',
    (r'^$', TemplateView.as_view(template_name="index.html")),
    (r'^admin/', include(admin.site.urls)),
    (r'^browse/(.*)', django_databrowse.site.root),
)

urlpatterns += patterns('audit_cvrs.views',
    # (r'^$',                             'home', name='home'),
    # (r'^reports/(?P<contest>\w*)/$',    'report'),
    #(r'^selections/(?P<contest>\w*)/$', 'report'),
)

# Generic views

urlpatterns += patterns('django.views.generic.list',
    #(r'^reports/$',                     'ListView',     dict(cvr_dict, template_name="audit_cvrs/reports.html")),
    (r'^selections/$',                  ListView.as_view(model=CVR))
)
