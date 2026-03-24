---
title: FinControl - Guía de Despliegue
aliases:
  - Despliegue
  - Deployment
tags:
  - fincontrol
  - deployment
  - infraestructura
  - produccion
related:
  - "[[ARCHITECTURE]]"
  - "[[CONFIGURATION]]"
status: completado
created: 2026-03-24
updated: 2026-03-24
---

# FinControl — Guía de Despliegue

> [!info] Documentación relacionada
> - [[ARCHITECTURE|Arquitectura del Sistema]] — Stack tecnológico y estructura
> - [[CONFIGURATION|Configuración y Despliegue]] — Variables de entorno y dependencias

---

## Requisitos previos

| Herramienta | Versión mínima | Instalación |
|-------------|---------------|-------------|
| Docker Desktop | 4.x | https://docs.docker.com/get-docker/ |
| mkcert | 1.4.x | https://github.com/FiloSottile/mkcert |
| Git | 2.x | https://git-scm.com/ |

**mkcert en Windows (Chocolatey):**
```powershell
choco install mkcert
```

**mkcert en macOS (Homebrew):**
```bash
brew install mkcert
```

---

## Primer despliegue (producción local)

### 1. Clonar el repositorio

```bash
git clone <url-del-repo> fincontrol
cd fincontrol
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` y cambiar **todos** los valores marcados como `change-me`:

```env
SECRET_KEY=<cadena aleatoria larga>
POSTGRES_PASSWORD=<contraseña segura>
JWT_SECRET_KEY=<cadena aleatoria larga>
```

Para generar valores seguros:
```bash
# Linux/macOS
openssl rand -hex 32

# PowerShell
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Para producción, ajustar también:
```env
APP_ENV=production
DEBUG=false
BACKEND_WORKERS=4
VITE_API_URL=https://localhost/api
```

### 3. Generar certificados SSL locales

```bash
bash scripts/generate-certs.sh
```

Esto instala la CA raíz de mkcert en el sistema y genera:
- `nginx/certs/localhost.pem`
- `nginx/certs/localhost-key.pem`

> [!warning] Los certificados no se commitean al repositorio (están en `.gitignore`). Cada máquina debe generarlos.

### 4. Levantar todos los servicios

```bash
docker compose up -d --build
```

La primera vez tarda varios minutos (descarga imágenes, compila frontend, instala dependencias Python).

### 5. Verificar estado

```bash
docker compose ps
```

Todos los servicios deben aparecer como **healthy**:

```
NAME                    STATUS
fincontrol-nginx        Up (healthy)
fincontrol-api          Up (healthy)
fincontrol-frontend     Up (healthy)
fincontrol-ml           Up (healthy)
fincontrol-db           Up (healthy)
fincontrol-redis        Up (healthy)
fincontrol-celery-worker Up (healthy)
fincontrol-celery-beat  Up (healthy)
fincontrol-backup       Up
```

### 6. Acceder a la aplicación

| URL | Descripción |
|-----|-------------|
| https://localhost | Frontend SvelteKit |
| https://localhost/api/docs | Swagger UI del backend |
| https://localhost/api/health | Health check del backend |

> [!note] El navegador confiará en el certificado automáticamente porque mkcert instala la CA raíz en el sistema operativo.

---

## Entorno de desarrollo

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

| URL | Descripción |
|-----|-------------|
| http://localhost:3000 | Frontend (HMR activo) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8001/docs | ML Service Swagger |

---

## Operaciones habituales

### Ver logs

```bash
# Todos los servicios
docker compose logs -f

# Solo el backend
docker compose logs -f backend

# Solo nginx
docker compose logs -f nginx
```

### Reiniciar un servicio

```bash
docker compose restart backend
```

### Actualizar la aplicación

```bash
git pull
docker compose up -d --build
```

Docker solo reconstruye los servicios con cambios; los datos persisten en los volúmenes.

### Ejecutar migraciones Alembic

```bash
docker compose exec backend alembic upgrade head
```

---

## Backups de PostgreSQL

### Backup manual

```bash
docker exec fincontrol-backup pg-backup.sh
```

### Ver backups disponibles

```bash
docker exec fincontrol-backup ls -lh /backups/
```

### Listar desde el host (volumen Docker)

```bash
docker run --rm \
  -v fincontrol_postgres_backups:/backups \
  alpine ls -lh /backups/
```

### Restaurar un backup

```bash
# 1. Copiar el backup al host
docker cp fincontrol-backup:/backups/fincontrol_20260324_020000.sql.gz ./

# 2. Restaurar en el contenedor de PostgreSQL
gunzip -c fincontrol_20260324_020000.sql.gz \
  | docker exec -i fincontrol-db \
    psql -U fincontrol fincontrol
```

### Programación automática

El servicio `postgres-backup` ejecuta un backup al arrancar y luego cada día a las **02:00** (hora del contenedor). Los backups se conservan **7 días** por defecto (configurable con `BACKUP_KEEP_DAYS` en `.env`).

---

## Diferencias dev vs producción

| Aspecto | Desarrollo (`docker-compose.dev.yml`) | Producción (`docker-compose.yml`) |
|---------|--------------------------------------|-----------------------------------|
| SSL | No (HTTP puro) | Sí (mkcert, HTTPS) |
| Proxy | No (puertos directos) | Nginx reverse proxy |
| Hot reload | Sí (`--reload` en uvicorn) | No (`--workers 4`) |
| Bind mounts src | Sí (cambios en tiempo real) | No (imagen autocontenida) |
| Puertos expuestos | 8000, 3000, 8001, 5432, 6379 | 80, 443 (solo nginx) |
| Workers uvicorn | 1 | 4 |
| Frontend | `npm run dev` (Vite) | `node build` (adapter-node) |
| Backups | No | Sí (diarios a las 02:00) |
| Variables debug | `DEBUG=true` | `DEBUG=false` |

---

## Estructura de archivos de infraestructura

```
├── docker-compose.yml        # Producción
├── docker-compose.dev.yml    # Desarrollo
├── nginx/
│   ├── nginx.conf            # Config dev (HTTP)
│   ├── nginx.prod.conf       # Config prod (HTTPS)
│   └── certs/                # Certificados mkcert (.gitignored)
│       ├── localhost.pem
│       └── localhost-key.pem
├── scripts/
│   ├── generate-certs.sh     # Genera certificados SSL locales
│   └── pg-backup.sh          # Script de backup PostgreSQL
├── backend/
│   └── Dockerfile
├── frontend/
│   ├── Dockerfile            # Desarrollo (Vite dev server)
│   └── Dockerfile.prod       # Producción (build + adapter-node)
└── ml-service/
    └── Dockerfile
```

---

## Solución de problemas

### El certificado no es de confianza en el navegador

```bash
# Reinstalar la CA raíz de mkcert
mkcert -install
# Regenerar certificados
bash scripts/generate-certs.sh
```

### Un servicio no alcanza el estado "healthy"

```bash
# Ver logs del servicio con problemas
docker compose logs backend

# Inspeccionar el resultado del health check
docker inspect fincontrol-api | jq '.[0].State.Health'
```

### Nginx devuelve 502 Bad Gateway

El backend o el frontend no están listos. Verificar:
```bash
docker compose ps
docker compose logs backend
```

### El backup falla por credenciales

Verificar que `POSTGRES_PASSWORD` en `.env` coincide con la contraseña del contenedor postgres. Si el contenedor ya existe con otra contraseña, eliminar el volumen y recrear:
```bash
docker compose down -v  # CUIDADO: elimina todos los datos
docker compose up -d --build
```
