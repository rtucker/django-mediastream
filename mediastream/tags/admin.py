from django.contrib import admin
from django.contrib.contenttypes.generic import GenericStackedInline
from models import Tag, TaggedItem

class TaggedItemInline(GenericStackedInline):
    model = TaggedItem

class TagAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'count_objects']
    readonly_fields = ['list_objects']

    ordering = ['parent', 'label']

    def count_objects(self, obj):
        return len(obj.get_taggeditems())
    count_objects.short_description = 'Tagged'

    def list_objects(self, obj):
        out = []
        for thing in obj.get_taggeditems():
            out.append('<p>{0} > <strong>{1}</strong> ({2})</p>'.format(thing.tag, thing.content_object, thing.content_type))
        return ''.join(out)
    list_objects.short_description = 'Objects tagged'
    list_objects.allow_tags = True

admin.site.register(Tag, TagAdmin)


