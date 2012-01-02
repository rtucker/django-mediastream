from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class Tag(models.Model):
    label = models.SlugField()
    parent = models.ForeignKey("self", blank=True, null=True)

    def __unicode__(self):
        return u' > '.join([f.label for f in self.get_hierarchy_climb()])

    def get_taggeditems(self):
        pile = []
        for node in self.get_hierarchy_descend():
            pile.extend(node.taggeditem_set.all())
        return pile
    
    def get_hierarchy_climb(self):
        node = self
        tree = []
        while True:
            tree.append(node)
            if node.parent:
                node = node.parent
            else:
                break
        tree.reverse()
        return tree

    def get_hierarchy_descend(self, start=None):
        node = start or self
        tree = [node]

        for child in node.tag_set.all():
            tree.extend(self.get_hierarchy_descend(child))

        return tree

class TaggedItem(models.Model):
    tag = models.ForeignKey(Tag)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return u"{0} ({1}, {2})".format(
            self.content_object.__unicode__(),
            self.content_type.__unicode__(),
            self.tag.__unicode__(),
        )
