from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import json
from decimal import Decimal
from nomina.models import Empleado, RegistraAsistencia

VERIFY_TOKEN = "inemo123"

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse(status=403)

    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        try:
            msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
            telefono = msg["from"]
            texto = msg.get("text", {}).get("body", "").lower().strip()

            empleado = Empleado.objects.filter(curp__icontains=telefono[-8:]).first()
            if not empleado:
                return JsonResponse({"status": "error", "msg": "Empleado no encontrado"})

            # Detectar acción
            if "entra" in texto:
                RegistraAsistencia.objects.create(
                    empleado=empleado,
                    fecha_hora_entrada=timezone.now(),
                    latitud=0.0,
                    longitud=0.0,
                    origen="whatsapp"
                )
                return JsonResponse({"status": "ok", "msg": "Entrada registrada"})

            elif "sal" in texto:
                registro = RegistraAsistencia.objects.filter(
                    empleado=empleado, fecha_hora_salida__isnull=True
                ).last()
                if registro:
                    registro.fecha_hora_salida = timezone.now()
                    registro.save()
                    return JsonResponse({"status": "ok", "msg": "Salida registrada"})
                else:
                    return JsonResponse({"status": "error", "msg": "No hay entrada previa registrada"})

            return JsonResponse({"status": "ok", "msg": "Comando no reconocido"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
