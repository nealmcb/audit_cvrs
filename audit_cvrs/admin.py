from django.forms import TextInput, Textarea
from django.contrib import admin
from audit_cvrs.models import *
import reversion

class CVRInline(admin.TabularInline):
    model = CVR

class CountyElectionAdmin(admin.ModelAdmin):
    inlines = [ CVRInline, ]

class CVRAdmin(reversion.VersionAdmin):
    "Modify default layout of admin form"
    list_display = ('name', 'status', 'discrepancy')

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':30, 'cols':40})},
    }

admin.site.register(CountyElection, CountyElectionAdmin)
admin.site.register(CVR, CVRAdmin)
