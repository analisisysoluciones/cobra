@echo off
echo ===============================
echo 🔄 Iniciando despliegue...
echo ===============================

:: Ir a la carpeta del proyecto
cd /d c:\proyectos\cobra/cobra

:: Obtener los últimos cambios de Git
echo 🚀 Obteniendo cambios del repositorio...
git pull origin main

:: Activar entorno virtual
echo 🏗 Activando entorno virtual...
call venv\Scripts\activate.bat

:: Instalar dependencias
echo 📦 Instalando dependencias...
pip install -r requirements.txt

:: Aplicar migraciones
echo 🔄 Aplicando migraciones...
python manage.py migrate

:: Recopilar archivos estáticos
echo 🎨 Recopilando archivos estáticos...
python manage.py collectstatic --noinput

:: Reiniciar servidor (Si usas Gunicorn, Django runserver o algún servicio)
echo 🔄 Reiniciando servidor...
taskkill /f /im python.exe
start cmd /k "call venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000"

echo ✅ Despliegue completado.
exit
