from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def flotilla_captura(request):

    return render(request, "flotilla/captura.html")



