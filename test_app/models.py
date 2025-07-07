from django.db import models

class Product(models.Model):
    Name = models.CharField(max_length=255)
    Seller = models.CharField(max_length=255)
    Rating = models.FloatField()
    Feedbacks = models.IntegerField()
    Sale_Price = models.FloatField()
    Price = models.FloatField()
    Article = models.CharField(max_length=20)

    def __str__(self):
        return self.Name