# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'AssetFile.contents'
        db.alter_column('assets_assetfile', 'contents', self.gf('django.db.models.fields.files.FileField')(max_length=255))


    def backwards(self, orm):
        
        # Changing field 'AssetFile.contents'
        db.alter_column('assets_assetfile', 'contents', self.gf('django.db.models.fields.files.FileField')(max_length=100))


    models = {
        'assets.album': {
            'Meta': {'ordering': "['name']", 'object_name': 'Album'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'discs': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_compilation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'assets.artist': {
            'Meta': {'ordering': "['name']", 'object_name': 'Artist'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
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
            'mimetype': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'assets.track': {
            'Meta': {'ordering': "('_order',)", 'object_name': 'Track', '_ormbases': ['assets.Asset']},
            '_order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'album': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Album']"}),
            'artist': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assets.Artist']"}),
            'asset_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['assets.Asset']", 'unique': 'True', 'primary_key': 'True'}),
            'bpm': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'disc_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'track_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['assets']
