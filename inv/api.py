from .models import Categoria, Material, Unidad, Requisicion, ItemRequisicion, Firma
from nomina.models import Empleado
from django.core.files.base import ContentFile
import base64
import json
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View

class FirmaAPI(View):
    def post(self, request):
        data = json.loads(request.body)
        requisicion_id = data.get('requisicion_id')
        firma_data = data.get('firma')  # Imagen en base64
        usuario_id = data.get('usuario_id')
        
        requisicion = Requisicion.objects.get(id=requisicion_id)
        usuario = Empleado.objects.get(id=id)
        
        # Guardar la firma
        format, imgstr = firma_data.split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(base64.b64decode(imgstr), name=f'firma_{requisicion.folio}.{ext}')
        
        firma = Firma(requisicion=requisicion, usuario=usuario, imagen_firma=data)
        firma.save()
        
        return JsonResponse({'status': 'success', 'message': 'Firma guardada'})