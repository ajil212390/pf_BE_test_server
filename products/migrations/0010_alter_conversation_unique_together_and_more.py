import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_commitment'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='image_file',
            field=models.ImageField(blank=True, null=True, upload_to='chat_images/'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='conversation',
                    unique_together=set(),
                ),
                migrations.AddField(
                    model_name='conversation',
                    name='conversation_type',
                    field=models.CharField(default='customer', max_length=20),
                ),
                migrations.AddField(
                    model_name='conversation',
                    name='executive',
                    field=models.ForeignKey(blank=True, db_column='executiveid', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='products.supplierexecutive'),
                ),
                migrations.AlterField(
                    model_name='conversation',
                    name='enduser',
                    field=models.ForeignKey(blank=True, db_column='endsuerid', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='products.enduser'),
                ),
            ],
            database_operations=[],
        ),
    ]
