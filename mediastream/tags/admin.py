from django.contrib import admin
from django.contrib.contenttypes.generic import GenericInlineModelAdmin
from models import Tag, TaggedItem

class TagAdmin(admin.ModelAdmin):
    pass
admin.site.register(Tag, TagAdmin)

class TaggedItemInline(GenericInlineModelAdmin):
    model = TaggedItem
