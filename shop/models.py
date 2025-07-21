from django.db import models
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=200,
                            db_index=True)
    slug = models.SlugField(max_length=200,
                            unique=True)
    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def get_absolute_url(self):
        return reverse('shop:product_list_by_category',
                        args=[self.slug])

    def __str__(self):
        return self.name



class Product(models.Model):
    category = models.ForeignKey(Category,
                                related_name='products',
                                on_delete=models.CASCADE)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d',
                            blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
   
    class Meta:
        ordering = ('name',)
        # index_together = (('id', 'slug'),)
        indexes = [
            models.Index(fields=['id', 'slug']),
        ]

    def get_absolute_url(self):
        return reverse('shop:product_detail',
                        args=[self.id, self.slug])

    def __str__(self):
        return self.name

    def suggest_products_for(self, products, max_results=6):
        product_ids = [p.id for p in products]
        if len(products) == 1:
            # only 1 product
            suggestions = r.zrange(
                            self.get_product_key(product_ids[0]),
                            0, -1, desc=True)[:max_results]
        else:
            # generate a temporary key
            flat_ids = ''.join([str(id) for id in product_ids])
            tmp_key = f'tmp_{flat_ids}'
            # multiple products, combine scores of all products
            # store the resulting sorted set in a temporary key
            keys = [self.get_product_key(id) for id in product_ids]
            r.zunionstore(tmp_key, keys)
            # remove ids for the products the recommendation is for
            r.zrem(tmp_key, *product_ids)
            # get the product ids by their score, descendant sort
            suggestions = r.zrange(tmp_key, 0, -1,
                                desc=True)[:max_results]
            # remove the temporary key
            r.delete(tmp_key)
        suggested_products_ids = [int(id) for id in suggestions]
         # get suggested products and sort by order of appearance
        suggested_products = list(Product.objects.filter(id__in=suggested_products_ids))
        suggested_products.sort(key=lambda x: suggested_products_ids.index(x.id))
        return suggested_products

    def clear_purchases(self):
        for id in Product.objects.values_list('id', flat=True):
            r.delete(self.get_product_key(id))