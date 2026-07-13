from django.db import models

class Productcategory(models.Model):
    productcategoryid = models.AutoField(primary_key=True)
    productcategoryname = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'productcategory'

class Productunit(models.Model):
    productunitid = models.AutoField(primary_key=True)
    productunitname = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'productunit'

class Company(models.Model):
    companyid = models.AutoField(primary_key=True)
    companyname = models.CharField(max_length=200)
    companyphonenumber = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'company'

class Users(models.Model):
    userid = models.AutoField(primary_key=True)
    username = models.CharField(max_length=120)
    useremail = models.CharField(unique=True, max_length=200, blank=True, null=True)
    userpassword = models.CharField(max_length=120)
    companyid = models.ForeignKey(Company, models.DO_NOTHING, db_column='companyid', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'

class Products(models.Model):
    productid = models.AutoField(primary_key=True)
    productname = models.CharField(max_length=150)
    productcategoryid = models.ForeignKey(Productcategory, models.DO_NOTHING, db_column='productcategoryid', blank=True, null=True)
    productunitid = models.ForeignKey(Productunit, models.DO_NOTHING, db_column='productunitid', blank=True, null=True)
    productprice = models.DecimalField(max_digits=18, decimal_places=2)
    productphotopath = models.ImageField(upload_to='', max_length=2000, blank=True, null=True, db_column='productphotopath')
    dateadded = models.DateField(blank=True, null=True)
    userid = models.ForeignKey(Users, models.DO_NOTHING, db_column='userid', blank=True, null=True)
    companyid = models.ForeignKey(Company, models.DO_NOTHING, db_column='companyid', blank=True, null=True)
    createdat = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    addtype = models.CharField(max_length=10, default='Single', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'products'

