from django.contrib import admin

from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'date')
    search_fields = ('title', 'description', 'technologies')
    list_filter = ( 'date', 'technologies')
