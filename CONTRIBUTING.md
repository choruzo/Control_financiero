# Guía de contribución — FinControl

Gracias por tu interés en contribuir a FinControl. Este documento describe el flujo de trabajo, los estándares de código y los procesos para reportar bugs y proponer mejoras.

---

## Índice

1. [Cómo contribuir](#cómo-contribuir)
2. [Requisitos previos](#requisitos-previos)
3. [Setup del entorno de desarrollo](#setup-del-entorno-de-desarrollo)
4. [Estándares de código](#estándares-de-código)
5. [Tests obligatorios](#tests-obligatorios)
6. [Cómo reportar bugs](#cómo-reportar-bugs)
7. [Cómo proponer features](#cómo-proponer-features)
8. [Revisión de Pull Requests](#revisión-de-pull-requests)

---

## Cómo contribuir

1. **Fork** del repositorio en GitHub.
2. Crea una rama con el prefijo adecuado:
   - `feature/nombre-de-la-feature` — nueva funcionalidad
   - `fix/descripcion-del-bug` — corrección de bug
   - `docs/que-se-documenta` — cambios de documentación
   - `refactor/que-se-refactoriza` — refactorizaciones sin cambio de comportamiento
3. Realiza tus cambios con commits atómicos y descriptivos (ver [estándares de commits](#commits)).
4. Abre un **Pull Request** hacia `main` con una descripción clara de los cambios.
5. Espera la revisión. Se pueden pedir cambios antes de la fusión.

---

## Requisitos previos

| Herramienta | Versión mínima |
|-------------|---------------|
| Docker Desktop | 4.x |
| Git | 2.x |
| Python | 3.12 (solo si trabajas fuera de Docker) |
| Node.js | 20 LTS (solo si trabajas fuera de Docker) |

---

## Setup del entorno de desarrollo

```bash
# 1. Fork y clonar
git clone https://github.com/tu-usuario/fincontrol.git
cd fincontrol

# 2. Configurar variables de entorno
cp .env.example .env

# 3. Levantar el stack completo
docker compose -f docker-compose.dev.yml up --build
```

Servicios disponibles:

| Servicio | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API + Swagger | http://localhost:8000/docs |
| ML Service + Swagger | http://localhost:8001/docs |

### Desarrollo sin Docker (backend)

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Desarrollo sin Docker (frontend)

```bash
cd frontend
npm install
npm run dev
```

---

## Estándares de código

### Python (backend y ml-service)

- Formateador y linter: **Ruff** (`line-length = 100`)
- Reglas activas: `E, F, I, N, W, UP, B, SIM`
- Target: Python 3.12

```bash
# Verificar
docker compose -f docker-compose.dev.yml exec backend ruff check app/

# Aplicar correcciones automáticas
docker compose -f docker-compose.dev.yml exec backend ruff check --fix app/
docker compose -f docker-compose.dev.yml exec backend ruff format app/
```

### TypeScript / Svelte (frontend)

- Linter: **ESLint** (flat config v9) + plugin-svelte
- Formateador: **Prettier** 3.x

```bash
cd frontend
npm run lint          # Verificar
npm run lint:fix      # Corregir automáticamente
npm run format        # Formatear con Prettier
npm run format:check  # Verificar formato
```

### Commits

Usa el formato **Conventional Commits**:

```
tipo(scope): descripción breve en imperativo

[cuerpo opcional]
```

Tipos válidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`

Ejemplos:
```
feat(transactions): add CSV import with dry-run mode
fix(ml): correct confidence threshold for auto-assign
docs(readme): add quickstart section
```

---

## Tests obligatorios

**Todo cambio de código debe ir acompañado de tests.** Un PR sin tests no se considera completo.

### Backend

```bash
# Ejecutar todos los tests con cobertura
docker compose -f docker-compose.dev.yml exec backend pytest --cov=app -v

# Cobertura mínima requerida: 80%
# La CI fallará si se baja de ese umbral
```

### Frontend

```bash
cd frontend
npm run lint           # Sin errores ESLint
npm run test:e2e       # Tests E2E con Playwright
```

### ML Service

```bash
docker compose -f docker-compose.dev.yml exec ml-service ruff check app/
```

---

## Cómo reportar bugs

Abre un [issue](https://github.com/tu-usuario/fincontrol/issues/new) con la siguiente información:

**Título:** `[Bug] Descripción breve del problema`

**Contenido mínimo:**
- Versión de Docker Desktop y sistema operativo
- Pasos exactos para reproducir el problema
- Comportamiento esperado vs. comportamiento actual
- Logs relevantes (output de `docker compose logs servicio`)
- Si aplica: capturas de pantalla o respuesta de la API

---

## Cómo proponer features

1. Abre un [issue](https://github.com/tu-usuario/fincontrol/issues/new) antes de empezar a implementar.
2. Describe el caso de uso, el problema que resuelve y la solución propuesta.
3. Consulta el [Roadmap](Docs/ROADMAP.md) para asegurarte de que no está ya planificado.
4. Espera el visto bueno de los mantenedores antes de abrir el PR.

---

## Revisión de Pull Requests

### Criterios de aceptación

- [ ] Los tests pasan en CI (GitHub Actions: backend, frontend, ml-service)
- [ ] Cobertura de backend >= 80%
- [ ] Sin errores de lint (Ruff, ESLint)
- [ ] Tests E2E pasan (Playwright)
- [ ] Los cambios están documentados si afectan a la API, modelos de datos o arquitectura
- [ ] El `ROADMAP.md` y `CLAUDE.md` están actualizados si corresponde

### Checklist pre-PR

Antes de abrir tu PR, verifica:

```bash
# Backend
docker compose -f docker-compose.dev.yml exec backend ruff check app/
docker compose -f docker-compose.dev.yml exec backend pytest --cov=app

# Frontend
cd frontend && npm run lint && npm run test:e2e
```
