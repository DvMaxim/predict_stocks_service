# Generated by Django 4.0.4 on 2022-12-09 11:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('order', '0001_initial'),
        ('product', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordered_product',
            name='product_Id',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.SET_DEFAULT, to='product.product'),
        ),
    ]