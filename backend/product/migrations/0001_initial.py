# Generated by Django 4.0.4 on 2022-12-09 11:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('cart_Id', models.AutoField(primary_key=True, serialize=False)),
                ('total_Amount', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_id', models.CharField(max_length=50)),
                ('category_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('product_Id', models.AutoField(primary_key=True, serialize=False)),
                ('product_Name', models.CharField(max_length=50)),
                ('product_Description', models.TextField(max_length=700)),
                ('product_Price', models.FloatField()),
                ('product_isSale', models.CharField(default='No', max_length=10)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(default='/product/default.png', upload_to='product')),
                ('product_category', models.ForeignKey(default='', on_delete=django.db.models.deletion.SET_DEFAULT, to='product.category')),
            ],
        ),
        migrations.CreateModel(
            name='Product_In_Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('cart_Id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product.cart')),
                ('product_Id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product.product')),
            ],
        ),
    ]
