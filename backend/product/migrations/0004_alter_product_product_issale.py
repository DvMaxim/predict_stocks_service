# Generated by Django 4.0.4 on 2022-12-09 17:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0003_alter_product_product_issale'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='product_isSale',
            field=models.BooleanField(default=False),
        ),
    ]
