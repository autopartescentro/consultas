IA VIDRIOS AUTOPARTES CENTRO - VERSION ONLINE

Contenido:
- app.py
- requirements.txt
- carpeta listas_precios con los Excel fijos
- carpeta .streamlit con config y ejemplo de secrets

PASO 1 - Crear repositorio en GitHub
1. Entrar a github.com
2. Crear cuenta o iniciar sesión
3. New repository
4. Nombre sugerido: ia-vidrios-autopartes-centro
5. Crear repositorio
6. Upload files
7. Subir TODOS los archivos y carpetas de esta carpeta:
   app.py
   requirements.txt
   listas_precios
   .streamlit
8. Commit changes

PASO 2 - Publicar en Streamlit Cloud
1. Entrar a streamlit.io/cloud
2. Iniciar sesión con GitHub
3. New app
4. Elegir el repositorio ia-vidrios-autopartes-centro
5. Main file path: app.py
6. Deploy

PASO 3 - Cargar API KEY segura
IMPORTANTE: no pongas tu clave real dentro de GitHub.
En Streamlit Cloud:
1. Entrar a la app
2. Settings
3. Secrets
4. Pegar:

OPENAI_API_KEY="tu_clave_real"

5. Save
6. Reiniciar la app si hace falta

PASO 4 - Listas de precios fijas
Para agregar proveedores:
1. Subir cada Excel dentro de la carpeta listas_precios
2. El nombre del archivo será el proveedor
   Ejemplo: Pilkington.xlsx aparece como Pilkington
3. Hacer Commit changes en GitHub
4. Streamlit se actualiza solo o tocás Reboot

PASO 5 - Usar en celular
1. Abrir el link de Streamlit desde el celular
2. Menú del navegador
3. Agregar a pantalla de inicio

NOTAS
- La app compara proveedores y muestra el mejor precio.
- La búsqueda exige coincidencia de marca + modelo + año/generación.
- Si no encuentra, revisar que la lista tenga el nombre del modelo y el rango de año correctamente cargado.
