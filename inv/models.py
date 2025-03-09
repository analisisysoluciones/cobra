from django.db import models
from bases.models import ClaseModelo

# Create your models here.

class Categoria(ClaseModelo):
    descripcion = models.CharField(
        max_length=100,
        help_text='Descripcion de la categoria',
        unique=True
    )

    def __str__(self):
        return "{}".format(self.descripcion)
    
    def save(self):
        self.descripcion = self.descripcion.upper()
        super(Categoria, self).save()

    class Meta:
        verbose_name_plural = 'Categorias'
        verbose_name = 'Categoria'

class Unidad(models.Model):
    clave = models.CharField('Unidad:',max_length=15,unique=True)
    descripcion = models.CharField('Descripcion:',max_length=60)

    def __str__(self):
        return "{},{}".self.clave,self.descripcion
    
    def save(self):
        self.descripcion = self.descripcion.upper()
        self.clave = self.clave.upper()
        super(Unidad, self).save()

    class Meta:
        verbose_name = 'Unidad'
        verbose_name_plural = 'Undiades'

class Material(ClaseModelo):
    clave = models.CharField('clave', max_length=25, unique=True)
    descripcion = models.CharField('Descripcion:',max_length=120, blank=False, null=False)
    existencia = models.DecimalField('Existencia:', max_digits=12,decimal_places=3,default=0.000)
    minimo = models.DecimalField('Minimo:', max_digits=12,decimal_places=3,default=0.000)
    maximo = models.DecimalField('Maximo:', max_digits=12,decimal_places=3,default=0.000)
    unidad_medida = models.ForeignKey(Unidad, on_delete=models.CASCADE,null=True)

    def __str__(self):
        return str(self.id)
    
    def save(self):
        self.descripcion = self.descripcion.upper()
        self.clave = self.clave.upper()
        super(Material, self).save()


# tipo_gastos=[
#     ('Fijo','Fijo'),
#     ('Variable','Variable'),
#     ('Administrativo','Adminitrativo'),
#     ('Directo','Directo'),
#     ('Indirecto','Indirecto'),
#     ('Financiero','Financiero'),
#     ('Esencial','Esencial'),
#     ('Discrecional','Discrecional'),
# ]

# class Conceptos(models.Model):
#     descripcion=models.CharField('Descripcion',max_length=120)
#     tipo = models.CharField('Tipo',choices=tipo_gastos,default='Fijo')
    

    
    


