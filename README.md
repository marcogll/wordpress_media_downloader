<p align="center">
  <img src="https://raw.githubusercontent.com/marcogll/mg_data_storage/refs/heads/main/soul23/logo/soul23_logo.svg" width="110" alt="WordPress Media Downloader">
</p>

<h1 align="center">WordPress Media Downloader</h1>

<p align="center">
  CLI tool to download entire WordPress media libraries via the REST API, preserving original filenames and folder structure.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3a3a3a?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/WordPress-3a3a3a?style=flat-square&logo=wordpress&logoColor=white" alt="WordPress">
  <img src="https://img.shields.io/badge/REST_API-3a3a3a?style=flat-square&logo=fastapi&logoColor=white" alt="REST API">
  <img src="https://img.shields.io/badge/CLI-3a3a3a?style=flat-square&logo=gnubash&logoColor=white" alt="CLI">
  <img src="https://img.shields.io/badge/Cross_Platform-3a3a3a?style=flat-square&logo=linux&logoColor=white" alt="Cross Platform">
</p>

---

## Requisitos

- Python 3.8+
- Acceso administrativo al sitio WordPress (para crear Application Passwords)
- WordPress 5.6+ (Application Passwords nativos) o plugin [Application Passwords](https://wordpress.org/plugins/application-passwords/)

## Instalacion

### 1. Clonar el repositorio

```bash
git clone git@github.com:marcogll/wordpress_media_downloader.git
cd wordpress_media_downloader
```

### 2. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# o
venv\Scripts\activate      # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales

```bash
cp .env.example .env
```

Edita `.env` con tus datos:

```env
WP_SITE_URL=https://tusitio.com
WP_USERNAME=tu_usuario
WP_APP_PASSWORD=abcd efgh ijkl mnop qrst uvwx
DOWNLOAD_DIR=./downloads
SAVE_METADATA=true
PRESERVE_STRUCTURE=true
```

## Como crear un Application Password

1. Inicia sesion en el panel de WordPress como administrador
2. Ve a **Usuarios > Tu perfil**
3. Baja hasta la seccion **Application Passwords**
4. Escribe un nombre (ej: "Media Downloader") y haz clic en **Add New**
5. Copia la contrasena generada (solo aparece una vez)
6. Pegala en el archivo `.env` como `WP_APP_PASSWORD`

> **Nota**: Si usas un plugin de seguridad, asegurate de que no bloquee las solicitudes a `/wp-json/`.

## Uso

### Modo interactivo (sin .env)

```bash
python wp_media_downloader.py
```

El script te pedira:
- URL del sitio
- Username
- Application Password
- Directorio de descarga
- Si deseas guardar metadatos JSON
- Si deseas preservar la estructura de carpetas

Al final te preguntara si quieres guardar la configuracion en `.env`.

### Modo automatico (con .env)

Si ya configuraste el archivo `.env`, simplemente ejecuta:

```bash
python wp_media_downloader.py
```

Cargara la configuracion automaticamente y comenzara la descarga.

## Estructura de descarga

### Con `PRESERVE_STRUCTURE=true` (default)

```
downloads/
├── 2024/
│   ├── 01/
│   │   ├── imagen.jpg
│   │   ├── imagen.jpg.json
│   │   └── documento.pdf
│   └── 03/
│       └── video.mp4
└── 2025/
    └── 06/
        └── logo.png
```

### Con `PRESERVE_STRUCTURE=false`

```
downloads/
├── imagen.jpg
├── imagen.jpg.json
├── documento.pdf
├── video.mp4
└── logo.png
```

## Metadatos JSON

Cuando `SAVE_METADATA=true`, cada archivo descargado tiene un `.json` asociado con:

```json
{
  "id": 123,
  "title": "Mi imagen",
  "description": "Descripcion del archivo",
  "caption": "Pie de foto",
  "alt_text": "Texto alternativo",
  "mime_type": "image/jpeg",
  "media_type": "image",
  "source_url": "https://tusitio.com/wp-content/uploads/2024/01/imagen.jpg",
  "date": "2024-01-15T10:30:00",
  "modified": "2024-01-15T10:30:00",
  "author": 1,
  "media_details": {
    "width": 1920,
    "height": 1080,
    "sizes": { ... }
  }
}
```

## Comportamiento

- **Archivos existentes**: Se saltan automaticamente (no se sobrescriben)
- **Paginacion**: Descarga de 100 en 100 items hasta completar toda la biblioteca
- **Progreso**: Muestra contador en tiempo real `[actual/total] (porcentaje%)`
- **Errores**: Se registran y muestran al final del proceso
- **Interrupcion**: Puedes cancelar con `Ctrl+C` de forma segura

## Solucion de problemas

### Error 401 Unauthorized
- Verifica que el username sea correcto
- Asegurate de usar un **Application Password**, no tu contrasena normal
- Confirma que el usuario tenga permisos para acceder a la biblioteca de medios

### Error 403 Forbidden
- Tu usuario no tiene permisos suficientes
- Un plugin de seguridad puede estar bloqueando el acceso a la REST API
- Verifica que la REST API este habilitada (visita `tusitio.com/wp-json/`)

### No se puede conectar
- Verifica que la URL sea correcta (con `https://` y sin `/` al final)
- Comprueba que el sitio sea accesible desde tu red
- Si el sitio usa Cloudflare, puede haber proteccion anti-bot activada

### Archivos faltantes
- Algunos items de la API pueden ser imagenes procesadas (thumbnails) sin `source_url`
- Estos se saltan automaticamente y se cuentan como "skipped"

## Estructura del proyecto

```
wordpress_media_downloader/
├── wp_media_downloader.py   # Script principal
├── .env.example             # Plantilla de configuracion
├── .env                     # Tu configuracion (no commitear)
├── requirements.txt         # Dependencias de Python
├── downloads/               # Archivos descargados (se crea automaticamente)
└── README.md                # Este archivo
```
