# Authors: Marinho Brandao <marinho at gmail.com>
#          Guilherme M. Gondim (semente) <semente at taurinus.org>
# File: <your project>/admin/filterspecs.py
# From http://djangosnippets.org/snippets/1051/, with modifications

from django.db import models
from django.contrib.admin.filterspecs import FilterSpec, ChoicesFilterSpec
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _

class AlphabeticFilterSpec(ChoicesFilterSpec):
    """
    Adds filtering by first char (alphabetic style) of values in the admin
    filter sidebar. Set the alphabetic filter in the model field attribute
    'alphabetic_filter'.

    my_model_field.alphabetic_filter = True
    """

    def __init__(self, f, request, params, model, model_admin,
                 field_path=None):
        super(AlphabeticFilterSpec, self).__init__(f, request, params, model,
                                          model_admin, field_path=field_path)
        if f.model != model and f.model not in model._meta.parents:
            # Filtering by relation
            self.lookup = '%s__%s' % (f.model._meta.module_name, f.name)
            self.words = '%s %s' % (f.model._meta.verbose_name, f.verbose_name)
            values_list = f.model.objects.values_list(f.name, flat=True)
        elif f.model in model._meta.parents:
            # Field is inherited from a parent
            self.lookup = f.name
            self.words = '%s %s' % (model._meta.verbose_name, f.verbose_name)
            values_list = model.objects.values_list(f.name, flat=True)
        else:
            self.lookup = f.name
            self.words = f.verbose_name
            values_list = model.objects.values_list(f.name, flat=True)
        self.lookup_kwarg = '%s__istartswith' % self.lookup
        self.lookup_val = request.GET.get(self.lookup_kwarg, None)
        # getting the first char of values
        self.lookup_choices = sorted(list(
            set(val[0].upper() for val in values_list if val)))

    def choices(self, cl):
        yield {
            'selected': self.lookup_val is None,
            'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
            'display': _('All')}
        for val in self.lookup_choices:
            yield {
                'selected': smart_unicode(val) == self.lookup_val,
                'query_string': cl.get_query_string({self.lookup_kwarg: val}),
                'display': val.upper()}

    def title(self):
        return _('%s that starts with') % self.words

# registering the filter
FilterSpec.filter_specs.insert(0,
    (lambda f: getattr(f, 'alphabetic_filter', False),
    AlphabeticFilterSpec))
