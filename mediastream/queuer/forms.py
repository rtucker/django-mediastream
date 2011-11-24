# from http://blog.yawd.eu/2011/admin-site-widget-generic-relations-django/
from django.forms import ModelForm
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.db.models.fields.related import ManyToOneRel
from widgets import ContentTypeSelect
from models import AssetQueueItem, Album

class AdminAssetQueueItemForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(AdminAssetQueueItemForm, self).__init__(*args, **kwargs)
        try:
            model = self.instance.content_type.model_class()
            model_key = model._meta.pk.name
        except:
            model = Album
            model_key = 'id'
        self.fields['object_id'].widget = ForeignKeyRawIdWidget(rel=ManyToOneRel(model, model_key))
        self.fields['content_type'].widget.widget = ContentTypeSelect('lookup_id_object_id', 
                        self.fields['content_type'].widget.widget.attrs, 
                        self.fields['content_type'].widget.widget.choices)

    class Meta:
        model = AssetQueueItem
