# Generated by Django 4.0.4 on 2022-12-09 11:00

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('order_Id', models.AutoField(primary_key=True, serialize=False)),
                ('order_Status', models.CharField(choices=[('Order Pending', 'Order Pending'), ('Order Placed', 'Order Placed'), ('Delivered', 'Delivered'), ('Canceled', 'Canceled')], default='Order Placed', max_length=30)),
                ('order_Placment_Date', models.DateField(auto_now_add=True)),
                ('order_Placment_Time', models.TimeField(auto_now_add=True)),
                ('order_Delivery_Date', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
                ('order_Delivery_Time', models.CharField(default='2PM - 4PM', max_length=30)),
                ('destination_email', models.EmailField(default='maks.dvornik.2016@mail.ru', max_length=200)),
                ('total_Amount', models.FloatField()),
                ('note', models.CharField(default='', max_length=1000)),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('payment_Id', models.AutoField(primary_key=True, serialize=False)),
                ('payment_Status', models.CharField(choices=[('Pending', 'Pending'), ('Paid', 'Paid')], default='Pending', max_length=30)),
                ('payment_Type', models.CharField(default='Cash On Delivery', max_length=20)),
                ('amount_Paid', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='Ordered_Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('order_Id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='order.order')),
            ],
        ),
    ]