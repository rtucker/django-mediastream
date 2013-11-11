# From http://blog.yawd.eu/2011/admin-site-widget-generic-relations-django/
from itertools import chain
from django.utils.safestring import mark_safe
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache

from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

class ContentTypeSelect(forms.Select):

    _init_choices_cache = defaultdict(lambda: None)

    def __init__(self, lookup_id,  attrs=None, choices=()):
        self.lookup_id = lookup_id
        cache_key = __name__ + '.ContentTypeSelect.__init__.choices.' + lookup_id
        flat_choices = self._init_choices_cache[lookup_id]
        if flat_choices is None:
            flat_choices = cache.get(cache_key)
            self._init_choices_cache[lookup_id] = flat_choices
        if flat_choices is None:
            flat_choices = list(choices)
            cache.set(cache_key, flat_choices)
            self._init_choices_cache[lookup_id] = flat_choices
        return super(ContentTypeSelect, self).__init__(attrs, flat_choices)
        
    def render(self, name, value, attrs=None, choices=()):
        cache_key = __name__ + '.ContentTypeSelect.render.choices.' + name + '.' + str(value)
        output = cache.get(cache_key)
        if not output:
            if name.startswith('item_set'):
                itemset, number, field = name.split('-',3)
                lookup_id = self.lookup_id.replace('_id_', '_id_%s-%s-' % (itemset, number), 1)
            else:
                lookup_id = self.lookup_id
            output = super(ContentTypeSelect, self).render(name, value, attrs, choices)
            choices = chain(self.choices, choices)
            choiceoutput = 'var %s_choice_urls = {\n' % (attrs['id'].replace('-','__',))
            choiceoutlist = []
            ctype_t_dict = defaultdict(None)
            for choice in choices:
                try:
                    ctype_t = ctype_t_dict[int(choice[0])]
                    if not ctype_t:
                        ctype_t = cache.get('contenttypeselect__choice__%i' % int(choice[0]))
                        ctype_t_dict[int(choice[0])] = ctype_t
                    if not ctype_t:
                        ctype = ContentType.objects.get(pk=int(choice[0]))
                        ctype_t = (str(choice[0]), ctype.app_label, ctype.model, ctype.model_class()._meta.pk.name)
                        cache.set('contenttypeselect__choice__%i' % int(choice[0]), ctype_t)
                        ctype_t_dict[int(choice[0])] = ctype_t
                    choiceoutlist.append("'%s': '../../../%s/%s?t=%s'" % ctype_t)
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
            cache.set(cache_key, output)
        return mark_safe(u''.join(output))
