from django.contrib import admin
from audit_cvrs.models import *

class CVRInline(admin.TabularInline):
    model = CVR

class CountyElectionAdmin(admin.ModelAdmin):
    inlines = [ CVRInline, ]

"""
class VoteCountAdmin(admin.ModelAdmin):
    "Modify default layout of admin form"
    list_display = ['votes', 'choice', 'contest_batch']
"""

admin.site.register(CountyElection, CountyElectionAdmin)
admin.site.register(CVR)
