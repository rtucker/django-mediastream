# From http://blog.yawd.eu/2011/admin-site-widget-generic-relations-django/
from itertools import chain
from django.utils.safestring import mark_safe
from django import forms
from django.contrib.contenttypes.models import ContentType

class ContentTypeSelect(forms.Select):
    def __init__(self, lookup_id,  attrs=None, choices=()):
        self.lookup_id = lookup_id
        super(ContentTypeSelect, self).__init__(attrs, choices)
        
    def render(self, name, value, attrs=None, choices=()):
        if name.startswith('item_set'):
            itemset, number, field = name.split('-',3)
            lookup_id = self.lookup_id.replace('_id_', '_id_%s-%s-' % (itemset, number), 1)
        else:
            lookup_id = self.lookup_id
        output = super(ContentTypeSelect, self).render(name, value, attrs, choices)
        choices = chain(self.choices, choices)
        choiceoutput = 'var %s_choice_urls = {\n' % (attrs['id'].replace('-','__',))
        choiceoutlist = []
        for choice in choices:
            try:
                ctype = ContentType.objects.get(pk=int(choice[0]))
                choiceoutlist.append("'%s': '../../../%s/%s?t=%s'" % (
                    str(choice[0]), ctype.app_label, ctype.model,
                    ctype.model_class()._meta.pk.name))
            except:
                pass
        choiceoutput += ',\n'.join(choiceoutlist)
        choiceoutput += '};\n'
        output += ('<script type="text/javascript">\n'
                   '(function($) {\n'
                   '  $(document).ready( function() {\n'
                   '%(choiceoutput)s\n'
                   '    $(\'#%(id)s\').change(function (){\n'
                   '        console.log("FIRED on change. " + %(idclean)s_choice_urls[$(this).val()]);\n'
                   '        $(\'#%(fk_id)s\').attr(\'href\',%(idclean)s_choice_urls[$(this).val()]);\n'
                   '    });\n'
                   '  });\n'
                   '})(django.jQuery);\n'
                   '</script>\n' % { 'choiceoutput' : choiceoutput, 
                                    'id' : attrs['id'],
                                    'idclean': attrs['id'].replace('-','__'),
                                    'fk_id' : lookup_id
                                  })
        return mark_safe(u''.join(output))
