from django.forms import TextInput, Textarea
from django.contrib import admin
from audit_cvrs.models import *

class CVRInline(admin.TabularInline):
    model = CVR
    extra = 1

class CountyElectionAdmin(admin.ModelAdmin):
    inlines = [ CVRInline, ]

class CVRAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'discrepancy')

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows':30, 'cols':40})},
    }



"""
class VoteCountAdmin(admin.ModelAdmin):
    "Modify default layout of admin form"
    list_display = ['votes', 'choice', 'contest_batch']
"""

admin.site.register(CountyElection, CountyElectionAdmin)
admin.site.register(CVR, CVRAdmin)
