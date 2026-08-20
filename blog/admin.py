from django.contrib import admin

from .models import BlogPage, Reference

class ReferenceInline(admin.TabularInline):
    model = Reference
    extra = 1
    fields = ('title', 'url', 'author', 'publication', 'date')
    show_change_link = True


@admin.register(BlogPage)
class BlogPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'get_authors')
    search_fields = ('title', 'body')
    inlines = [ReferenceInline]

    def get_authors(self, obj):
        return ", ".join([author.name for author in obj.authors.all()])
    get_authors.short_description = 'Authors'
