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

class Companycategory(models.Model):
    categoryid = models.AutoField(primary_key=True)
    categoryname = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = 'companycategory'

class Company(models.Model):
    companyid = models.AutoField(primary_key=True)
    companyname = models.CharField(max_length=200)
    companyphonenumber = models.BigIntegerField(blank=True, null=True)
    companylocation = models.CharField(max_length=200, blank=True, null=True)
    companyaddress = models.TextField(blank=True, null=True)
    categoryid = models.ForeignKey(Companycategory, models.DO_NOTHING, db_column='categoryid', blank=True, null=True)

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

class Customer(models.Model):
    customerid = models.AutoField(primary_key=True)
    customername = models.CharField(max_length=200)
    customerphonenumber = models.CharField(max_length=20, blank=True, null=True)
    customeraddress = models.CharField(max_length=500, blank=True, null=True)
    customeremail = models.CharField(max_length=200, blank=True, null=True)
    customercurrentbal = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    customeropeningbal = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    customerpincode = models.CharField(max_length=20, blank=True, null=True)
    customergst = models.CharField(max_length=50, blank=True, null=True)
    customerstate = models.CharField(max_length=100, blank=True, null=True)
    customerpanno = models.CharField(max_length=20, blank=True, null=True)
    companyid = models.ForeignKey(Company, models.DO_NOTHING, db_column='companyid')

    class Meta:
        managed = False
        db_table = 'customer'

class Supplier(models.Model):
    supplierid = models.AutoField(primary_key=True)
    suppliername = models.CharField(max_length=200)
    supplierphonenumber = models.CharField(max_length=20, blank=True, null=True)
    supplieraddress = models.CharField(max_length=500, blank=True, null=True)
    supplieremail = models.CharField(max_length=200, blank=True, null=True)
    suppliercurrentbal = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    supplieropeningbal = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    supplierpincode = models.CharField(max_length=20, blank=True, null=True)
    suppliergst = models.CharField(max_length=50, blank=True, null=True)
    isconnected = models.SmallIntegerField(default=0, db_column='isconnected')
    supplierstate = models.CharField(max_length=100, blank=True, null=True)
    supplierpanno = models.CharField(max_length=20, blank=True, null=True)
    companyid = models.ForeignKey(Company, models.DO_NOTHING, db_column='companyid')

    class Meta:
        managed = False
        db_table = 'supplier'

class CustomerBill(models.Model):
    customerbillid = models.AutoField(primary_key=True)
    customerid = models.ForeignKey(Customer, models.DO_NOTHING, db_column='customerid')
    customerbillno = models.CharField(max_length=100)
    customerbilldate = models.DateField()
    customerbillamount = models.DecimalField(max_digits=18, decimal_places=2)
    customerbillduedate = models.DateField(blank=True, null=True)
    paidamount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    balance = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    narration = models.CharField(max_length=500, blank=True, null=True)
    customerbilltype = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'customerbill'

class SupplierBill(models.Model):
    supplierbillid = models.AutoField(primary_key=True)
    supplierid = models.ForeignKey(Supplier, models.DO_NOTHING, db_column='supplierid')
    supplierbillno = models.CharField(max_length=100)
    supplierbilldate = models.DateField()
    supplierbillamount = models.DecimalField(max_digits=18, decimal_places=2)
    supplierbillduedate = models.DateField(blank=True, null=True)
    paidamount = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    balance = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    narration = models.CharField(max_length=500, blank=True, null=True)
    supplierbilltype = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'supplierbill'

class EndUser(models.Model):
    endsuerid = models.AutoField(primary_key=True, db_column='endsuerid')  # DB typo, kept as-is
    endusername = models.CharField(max_length=100, unique=True, db_column='endusername')
    enduserpassword = models.CharField(max_length=100, blank=True, null=True, db_column='enduserpassword')
    enduseremail = models.CharField(max_length=100, blank=True, null=True, db_column='enduseremail')
    enduserphone = models.CharField(max_length=20, blank=True, null=True, db_column='enduserphone')

    class Meta:
        managed = False
        db_table = 'enduser'

class Supplieruser(models.Model):
    supplieruserid = models.AutoField(primary_key=True)
    supplierid = models.ForeignKey(Supplier, models.DO_NOTHING, db_column='supplierid', blank=True, null=True)
    suppliername = models.CharField(max_length=25, blank=True, null=True)
    supplierusername = models.CharField(max_length=25, blank=True, null=True)
    supplieruserphone = models.CharField(max_length=20, blank=True, null=True)
    supplieruseremail = models.CharField(max_length=30, blank=True, null=True)
    supplierusergstnumber = models.CharField(max_length=50, blank=True, null=True)
    supplieruseraddress = models.CharField(max_length=100, blank=True, null=True)
    supplieruserpassword = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'supplieruser'

class Conversation(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, models.DO_NOTHING, db_column='companyid')
    enduser = models.ForeignKey(EndUser, models.DO_NOTHING, db_column='endsuerid')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'conversation'
        unique_together = (('company', 'enduser'),)

class ChatMessage(models.Model):
    id = models.AutoField(primary_key=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=20) # 'company' or 'enduser'
    text_content = models.TextField(blank=True, null=True)
    audio_file = models.FileField(upload_to='chat_audio/', blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True, help_text="Duration in seconds")
    waveform = models.TextField(blank=True, null=True, help_text="JSON list of waveform floats")
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    order_status = models.CharField(max_length=20, default='pending')

    class Meta:
        managed = True
        db_table = 'chat_message'

class SupplierExecutive(models.Model):
    executiveid = models.AutoField(primary_key=True)
    manager = models.ForeignKey(Supplieruser, on_delete=models.CASCADE, related_name='executives')
    executive_name = models.CharField(max_length=100)
    executive_username = models.CharField(max_length=100, unique=True)
    executive_password = models.CharField(max_length=100)
    executive_phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'supplier_executive'

class ExecutiveAllocation(models.Model):
    allocation_id = models.AutoField(primary_key=True)
    executive = models.ForeignKey(SupplierExecutive, on_delete=models.CASCADE, related_name='allocations')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='executive_allocations')
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'executive_allocation'
        unique_together = (('executive', 'company'),)

class SupplierOrder(models.Model):
    order_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column='companyid')
    supplier = models.ForeignKey(Supplier, on_delete=models.DO_NOTHING, db_column='supplierid')
    executive = models.ForeignKey(SupplierExecutive, on_delete=models.SET_NULL, blank=True, null=True, related_name='orders_taken')
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=50, default='Pending') # Pending, Approved, Delivered
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    gps_longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'supplier_order'

class SupplierOrderItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(SupplierOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.DO_NOTHING, db_column='productid')
    quantity = models.IntegerField()
    price_at_order = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'supplier_order_item'