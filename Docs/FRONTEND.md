---
title: FinControl - Frontend
aliases:
  - Frontend
  - SvelteKit
  - Dashboard
  - UI
tags:
  - fincontrol
  - frontend
  - sveltekit
  - typescript
  - skeleton-ui
  - tailwind
related:
  - "[[ARCHITECTURE]]"
  - "[[API_REFERENCE]]"
  - "[[CONFIGURATION]]"
  - "[[TESTING]]"
status: activo
created: 2026-03-22
updated: 2026-03-22
---

# FinControl - Frontend

> [!info] Documentación relacionada
> - [[ARCHITECTURE|Arquitectura]] — Stack tecnológico y decisiones de diseño
> - [[API_REFERENCE|Referencia de API]] — Endpoints consumidos por el frontend
> - [[CONFIGURATION|Configuración]] — Variables de entorno y Docker
> - [[TESTING|Guía de Testing]] — Tests unitarios e integración del frontend

---

## Visión General

El frontend de FinControl es una **SPA (Single Page Application)** construida con SvelteKit, TypeScript, Skeleton UI v2 y Tailwind CSS. Corre en el puerto 3000 con Hot Module Replacement (HMR) en desarrollo.

**Estado actual:** Fase 5.1 completada (infraestructura, auth, layout). Fases 5.2-5.8 (vistas funcionales) pendientes.

**Decisiones arquitectónicas clave:**
- **SSR deshabilitado** globalmente (`ssr: false`) — los tokens se almacenan en `localStorage`, inaccesible desde Node.js
- **Tema oscuro** por defecto (clase `dark` en `<html>`) con toggle claro/oscuro persistido
- **SvelteKit 2.12.1 pinado** sin `^` para mantener compatibilidad con Skeleton UI v2 (Svelte 4)

---

## Stack Tecnológico

| Componente | Versión | Propósito |
|------------|---------|-----------|
| SvelteKit | 2.12.1 | Framework fullstack (solo SPA mode) |
| Svelte | 4.2.19 | Engine reactivo |
| TypeScript | 5.5.4 | Tipado estático |
| Skeleton UI | 2.10.3 | Componentes UI accesibles |
| Tailwind CSS | 3.4.17 | Utility-first CSS |
| Vitest | 2.1.8 | Testing unitario |
| @testing-library/svelte | 5.2.4 | Testing de componentes |
| jsdom | 25.0.1 | DOM virtual para tests |

---

## Estructura de Archivos

```
frontend/
├── Dockerfile                    ← node:20-alpine, CMD npm run dev
├── package.json                  ← Dependencias pinadas
├── svelte.config.js              ← adapter-node, alias $lib
├── vite.config.ts                ← Proxy /api, Vitest config
├── tailwind.config.ts            ← Tema wintry, darkMode: 'class'
├── postcss.config.cjs            ← PostCSS + Tailwind
├── tsconfig.json                 ← Strict TypeScript
│
├── src/
│   ├── app.html                  ← HTML shell, lang="es", class="dark"
│   ├── app.postcss               ← @tailwind directives
│   │
│   ├── lib/
│   │   ├── types.ts              ← Interfaces TypeScript (Token, User, etc.)
│   │   ├── api/
│   │   │   ├── client.ts         ← apiFetch + refresh mutex
│   │   │   ├── auth.ts           ← login, register, getMe, refreshTokens
│   │   │   └── index.ts          ← Barrel exports
│   │   └── stores/
│   │       ├── auth.ts           ← authStore, isAuthenticated, currentUser
│   │       └── ui.ts             ← sidebarOpen, toggleSidebar
│   │
│   └── routes/
│       ├── +layout.ts            ← ssr: false (global)
│       ├── +layout.svelte        ← Skeleton init, theme
│       ├── login/
│       │   └── +page.svelte      ← Login/Registro (tabs)
│       └── (app)/                ← Route group protegido
│           ├── +layout.ts        ← Auth guard
│           ├── +layout.svelte    ← AppShell + sidebar + header
│           └── dashboard/
│               └── +page.svelte  ← KPI cards (placeholder)
│
├── static/
│   └── favicon.png
│
└── tests/
    ├── setup.ts                  ← Mocks de $app/*
    ├── unit/
    │   ├── api-client.test.ts    ← 11 tests
    │   └── auth-store.test.ts    ← 7 tests
    └── integration/
        └── login-page.test.ts    ← 7 tests
```

---

## 1. Cliente API (`lib/api/client.ts`)

### `apiFetch(path, options?) → Response`

Wrapper sobre `fetch` con gestión automática de tokens y refresh:

```typescript
const response = await apiFetch('/api/v1/accounts');
const data = await response.json();
```

**Características:**
- **Base URL**: `VITE_API_URL` (env) en browser, `http://backend:8000` en server
- **Authorization**: Añade `Bearer <access_token>` automáticamente
- **Content-Type**: Respeta `FormData` (no override), JSON por defecto
- **Request ID**: Header `X-Request-ID` en cada petición

### Refresh Token Mutex

```
Request A → 401
  ├── isRefreshing = false → Set true, call /auth/refresh
  │                           ├── Success → processQueue(newToken)
  │                           └── Fail → clearTokens() → /login
  │
Request B → 401 (simultáneo)
  └── isRefreshing = true → enqueue(resolve, reject)
                             (espera a que Request A complete el refresh)
```

**Problema resuelto:** Sin mutex, N requests simultáneas que reciban 401 generarían N llamadas a `/auth/refresh`, de las cuales N-1 fallarían (el token se revoca al rotar).

**Implementación:**
- `isRefreshing: boolean` — flag global
- `refreshQueue: Array<{resolve, reject}>` — cola de promesas pendientes
- `processQueue(token)` — resuelve todas las promesas encoladas con el nuevo token

### `apiFetchJson<T>(path, options?) → T`

Helper que valida status + parsea JSON:
```typescript
const accounts = await apiFetchJson<Account[]>('/api/v1/accounts');
```
Lanza `ApiError(status, message)` si el response no es OK.

### Gestión de Tokens

```typescript
getAccessToken(): string | null     // localStorage.getItem('fc_access_token')
getRefreshToken(): string | null    // localStorage.getItem('fc_refresh_token')
setTokens(access, refresh): void   // localStorage.setItem(...)
clearTokens(): void                // localStorage.removeItem(...)
```

**Prefix:** `fc_` para evitar colisiones con otras apps en localhost.

---

## 2. API de Autenticación (`lib/api/auth.ts`)

| Función | Método | Path | Content-Type | Notas |
|---------|--------|------|-------------|-------|
| `login(email, password)` | POST | `/api/v1/auth/login` | `form-data` | Campo `username` (requisito OAuth2) |
| `register(data)` | POST | `/api/v1/auth/register` | `json` | `{email, password}` |
| `getMe()` | GET | `/api/v1/auth/me` | — | Via interceptor (con token) |
| `refreshTokens(token)` | POST | `/api/v1/auth/refresh` | `json` | Fetch directo (sin interceptor) |

> [!warning] Login usa FormData, no JSON
> El endpoint `/auth/login` de FastAPI usa `OAuth2PasswordRequestForm`, que espera `application/x-www-form-urlencoded` con campo `username` (no `email`).

---

## 3. Stores (`lib/stores/`)

### Auth Store (`stores/auth.ts`)

Store Svelte writable para estado de autenticación:

```typescript
interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
```

**Métodos:**

| Método | Acción |
|--------|--------|
| `setSession(token, refreshToken, user?)` | Guarda tokens en localStorage + actualiza store |
| `loadUser()` | Llama `getMe()` para restaurar sesión tras reload |
| `logout()` | Limpia tokens + resetea store |

**Stores derivados:**
```typescript
export const isAuthenticated = derived(authStore, $s => $s.isAuthenticated);
export const currentUser = derived(authStore, $s => $s.user);
```

### UI Store (`stores/ui.ts`)

```typescript
export const sidebarOpen = writable(false);
export const toggleSidebar = () => sidebarOpen.update(v => !v);
```

---

## 4. Tipos TypeScript (`lib/types.ts`)

```typescript
interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;  // "bearer"
}

interface User {
  id: string;          // UUID
  email: string;
  is_active: boolean;
  created_at: string;  // ISO 8601
}

interface UserCreate {
  email: string;
  password: string;
}

interface ApiErrorResponse {
  detail: string | ValidationError[];
}

interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}
```

---

## 5. Rutas y Layouts

### Root Layout (`routes/+layout.ts`)

```typescript
export const ssr = false;  // SSR deshabilitado globalmente
```

**Justificación:** Los tokens viven en `localStorage`, que no existe en el contexto Node.js de SSR. Al ser una app personal en Docker, prerendering no aporta valor.

### Root Layout UI (`routes/+layout.svelte`)

```svelte
<script>
  import { initializeStores, Modal, Toast } from '@skeletonlabs/skeleton';
  import { computeLightSwitch } from '@skeletonlabs/skeleton';
  import { onMount } from 'svelte';

  initializeStores();  // Modal + Toast stores globales
  onMount(() => computeLightSwitch());  // Aplica tema guardado
</script>

<Modal />
<Toast />
<slot />
```

### Auth Guard (`routes/(app)/+layout.ts`)

```typescript
export const load = async () => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('fc_access_token');
    if (!token) {
      throw redirect(302, `/login?redirect=${encodeURIComponent(location.pathname)}`);
    }
  }
};
```

**Route group `(app)/`:** Todas las rutas dentro de este grupo requieren autenticación. El `(app)` no aparece en la URL.

### App Shell (`routes/(app)/+layout.svelte`)

Layout principal de la aplicación autenticada:

```
┌──────────────────────────────────────────────────┐
│  Header: Logo │ User email │ LightSwitch │ Logout │
├──────────┬───────────────────────────────────────┤
│          │                                       │
│ Sidebar  │          Content Area                 │
│          │            <slot />                   │
│ Dashboard│                                       │
│ Trans.   │                                       │
│ Budgets  │                                       │
│ Invest.  │                                       │
│ Mortgage │                                       │
│ Scenarios│                                       │
│ Settings │                                       │
│          │                                       │
└──────────┴───────────────────────────────────────┘
```

**Responsive:**
- **Desktop (≥ lg):** Sidebar fijo a la izquierda (`width-60`)
- **Mobile (< lg):** Sidebar como drawer (hamburger menu)

**Navegación (hardcoded):**
```typescript
const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/transactions', label: 'Transacciones', icon: '💳' },
  { path: '/budgets', label: 'Presupuestos', icon: '📋' },
  { path: '/investments', label: 'Inversiones', icon: '📈' },
  { path: '/mortgage', label: 'Hipoteca', icon: '🏠' },
  { path: '/scenarios', label: 'Escenarios', icon: '🔮' },
  { path: '/settings', label: 'Configuración', icon: '⚙️' },
];
```

**On mount:** Restaura sesión via `authStore.loadUser()` si hay token pero no hay usuario cargado.

### Login (`routes/login/+page.svelte`)

Página pública con tabs para login y registro:

**Tab Login:**
- Inputs: email + password
- Envía FormData con campo `username`
- On success: `setTokens()` → `loadUser()` → redirect a `?redirect=` (default `/dashboard`)
- Error display en tarjeta

**Tab Registro:**
- Inputs: email + password + confirmar password
- Validación client-side: passwords coinciden, mínimo 8 chars
- On success: mismo flujo que login

**Redirect preservado:** Si llegas a `/login?redirect=/investments`, tras login/registro te redirige a `/investments`.

### Dashboard (`routes/(app)/dashboard/+page.svelte`)

**Estado actual: Placeholder** para Fase 5.2.

4 tarjetas KPI con datos estáticos:
| Card | Valor | Nota |
|------|-------|------|
| Balance Total | — | Disponible en Fase 5.2 |
| Ingresos del Mes | — | Disponible en Fase 5.2 |
| Gastos del Mes | — | Disponible en Fase 5.2 |
| Tasa de Ahorro | — | Disponible en Fase 5.2 |

2 áreas placeholder para gráficos:
- Gráfico de cashflow (barras)
- Gráfico de gastos por categoría (donut)

---

## 6. Configuración de Build

### Vite (`vite.config.ts`)

```typescript
export default defineConfig({
  plugins: [sveltekit()],
  server: {
    host: '0.0.0.0',     // Accesible desde Docker
    port: 3000,
    proxy: {
      '/api': 'http://backend:8000'  // Para context SSR (no usado actualmente)
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['html']
    }
  }
});
```

### Tailwind (`tailwind.config.ts`)

```typescript
export default {
  darkMode: 'class',
  content: [
    './src/**/*.{html,js,svelte,ts}',
    // Skeleton plugin content paths
  ],
  plugins: [
    skeleton({ themes: { preset: ['wintry'] } })
  ]
};
```

**Tema `wintry`:** Paleta fría, tonos azules y grises. Compatible con modo oscuro y claro.

### SvelteKit (`svelte.config.js`)

```javascript
export default {
  kit: {
    adapter: adapter(),  // adapter-node para despliegue Docker
    alias: { '$lib': './src/lib' }
  }
};
```

---

## 7. Testing

### Setup (`tests/setup.ts`)

Mockea módulos de SvelteKit no disponibles en jsdom:
```typescript
vi.mock('$app/environment', () => ({ browser: true, dev: true }));
vi.mock('$app/navigation', () => ({ goto: vi.fn(), invalidate: vi.fn() }));
vi.mock('$app/stores', () => ({
  page: readable({ url: new URL('http://localhost:3000') })
}));
```

### Tests Implementados

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `unit/api-client.test.ts` | 11 | Headers, refresh, mutex concurrencia, FormData |
| `unit/auth-store.test.ts` | 7 | setSession, logout, loadUser, estados |
| `integration/login-page.test.ts` | 7 | Render, errores, redirect, registro, tabs |

**Total:** 25 tests

**Comando:**
```bash
cd frontend && npm test
# o
cd frontend && npx vitest run --coverage
```

---

## 8. Docker

### Dockerfile
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### docker-compose.dev.yml
```yaml
frontend:
  build: ./frontend
  ports:
    - "${FRONTEND_PORT:-3000}:3000"
  volumes:
    - ./frontend/src:/app/src       # HMR: cambios en src se reflejan al instante
    - ./frontend/static:/app/static
  environment:
    - VITE_API_URL=http://localhost:8000
  depends_on:
    - backend
```

**Volume mounts:** Solo `src/` y `static/` para HMR, no `node_modules/` (se instalan en la imagen).

---

## 9. Pendiente (Fases 5.2 - 5.8)

Las siguientes vistas están planificadas pero **aún no implementadas:**

| Fase | Vista | Datos de API |
|------|-------|-------------|
| 5.2 | Dashboard con KPIs reales | [[API_REFERENCE#8. Analytics (`/analytics`)\|analytics/overview]] |
| 5.2 | Gráfico de cashflow | [[API_REFERENCE#`GET /api/v1/analytics/cashflow`\|analytics/cashflow]] |
| 5.2 | Gráfico gastos por categoría | [[API_REFERENCE#`GET /api/v1/analytics/expenses-by-category`\|expenses-by-category]] |
| 5.3 | Tabla de transacciones | [[API_REFERENCE#4. Transacciones (`/transactions`)\|transactions]] |
| 5.3 | Importación CSV | [[API_REFERENCE#`POST /api/v1/transactions/import/csv`\|import/csv]] |
| 5.4 | Presupuestos | [[API_REFERENCE#5. Presupuestos (`/budgets`)\|budgets]] |
| 5.5 | Inversiones | [[API_REFERENCE#6. Inversiones (`/investments`)\|investments]] |
| 5.6 | Simulador hipotecario | [[API_REFERENCE#7. Simulador Hipotecario (`/mortgage`)\|mortgage]] |
| 5.7 | Predicciones y escenarios | [[API_REFERENCE#11. Escenarios What-If (`/scenarios`)\|scenarios]] |
| 5.8 | Configuración | [[API_REFERENCE#9. Fiscalidad (`/tax`)\|tax]] |

**Librería de gráficos planificada:** Apache ECharts (configurada en el [[ROADMAP|roadmap]] pero aún no integrada).
