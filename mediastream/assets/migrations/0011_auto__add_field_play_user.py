# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Play.user'
        db.add_column('assets_play', 'user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Play.user'
        db.delete_column('assets_play', 'user_id')


    models = {
        'assets.album': {
            'Meta': {'ordering': "['name']", 'object_name': 'Album'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'discogs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Discogs']", 'null': 'True', 'blank': 'True'}),
            'discs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'extra_artists': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'album_credits'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['assets.Artist']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_compilation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'assets.artist': {
            'Meta': {'ordering': "['name']", 'object_name': 'Artist'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'discogs': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Discogs']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_prince': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'assets.asset': {
            'Meta': {'object_name': 'Asset'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_assets'", 'null': 'True', 'to': "orm['auth.User']"}),
            'shared_with': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'shared_assets'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'shared_with_all': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'assets.assetdescriptor': {
            'Meta': {'ordering': "['bitstream']", 'unique_together': "(('assetfile', 'bitstream'),)", 'object_name': 'AssetDescriptor'},
            'assetfile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.AssetFile']"}),
            'bit_rate': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'bitstream': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_vbr': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'lossy': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'mimetype': ('django.db.models.fields.CharField', [], {'default': "'application/octet-stream'", 'max_length': '255'}),
            'sample_rate': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        },
        'assets.assetfile': {
            'Meta': {'ordering': "('_order',)", 'object_name': 'AssetFile'},
            '_order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Asset']"}),
            'contents': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mimetype': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'assets.discogs': {
            'Meta': {'ordering': "('object_type', 'object_id')", 'unique_together': "(('object_type', 'object_id'),)", 'object_name': 'Discogs'},
            'data_cache': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'data_cache_dttm': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'object_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'assets.play': {
            'Meta': {'object_name': 'Play'},
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Asset']"}),
            'context': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_groove': ('django.db.models.fields.NullBooleanField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'played': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'previous_play': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Play']", 'null': 'True', 'blank': 'True'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['queuer.AssetQueue']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'assets.rating': {
            'Meta': {'object_name': 'Rating'},
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Asset']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'play': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Play']", 'null': 'True', 'blank': 'True'}),
            'rating': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'assets.track': {
            'Meta': {'ordering': "('_order',)", 'object_name': 'Track', '_ormbases': ['assets.Asset']},
            '_order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'album': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Album']"}),
            'artist': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Artist']"}),
            'asset_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['assets.Asset']", 'unique': 'True', 'primary_key': 'True'}),
            'bpm': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'disc_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'extra_artists': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'track_credits'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['assets.Artist']"}),
            'length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'skip_random': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'track_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'queuer.assetqueue': {
            'Meta': {'object_name': 'AssetQueue'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['assets']
