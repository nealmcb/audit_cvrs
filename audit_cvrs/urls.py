from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView, ListView
from audit_cvrs.models import *
from reversion.models import Revision

admin.autodiscover()

cvr_dict = {
    'queryset': CVR.objects.all(),
}

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name="index.html")),
    url(r'^admin/', include(admin.site.urls)),
    #(r'^reports/$',                     'ListView',     dict(cvr_dict, template_name="audit_cvrs/reports.html")),
    url(r'^selections/$',                  ListView.as_view(model=CVR)),
    url(r'^auditingLog/$',                 ListView.as_view(model=Revision)),
]

#from audit_cvrs import views
#urlpatterns += ]
    # (r'^$',                             'home', name='home'),
    # (r'^reports/(?P<contest>\w*)/$',    'report'),
    #(r'^selections/(?P<contest>\w*)/$', 'report'),
#]
