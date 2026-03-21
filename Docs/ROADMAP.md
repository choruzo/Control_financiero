---
title: FinControl - Roadmap de Desarrollo
aliases:
  - Roadmap
  - Plan de desarrollo
tags:
  - fincontrol
  - roadmap
  - planificacion
  - fases
related:
  - "[[ARCHITECTURE]]"
status: en-progreso
created: 2026-03-21
updated: 2026-03-21
---

# FinControl - Roadmap de Desarrollo

> [!info] Documentación relacionada
> - [[ARCHITECTURE|Arquitectura del Sistema]] — Stack tecnológico, modelo de datos, endpoints API y estrategia ML

## Fases del Proyecto

---

## FASE 1: Fundamentos Backend (MVP Core)
**Objetivo:** Backend funcional con CRUD completo, autenticación y base de datos.

### 1.1 Infraestructura Base ✅
- [x] Configurar Docker Compose (PostgreSQL + Redis + Backend)
- [x] Crear proyecto FastAPI con estructura de carpetas
- [x] Configurar SQLAlchemy 2.0 async + Alembic
- [x] Variables de entorno con pydantic-settings
- [x] Logging estructurado

### 1.2 Autenticación
- [x] Modelo User
- [x] Registro y login con JWT
- [x] Refresh tokens
- [x] Middleware de autenticación
- [x] Tests de auth

### 1.3 Modelos Core ✅
- [x] Modelo Account (cuentas bancarias)
- [x] Modelo Category (categorías jerárquicas con subcategorías)
- [x] Modelo Transaction (transacciones con recurrencia)
- [x] Seeders: categorías por defecto (Alimentación, Transporte, Ocio, Hogar, Salud, etc.)
- [x] CRUD completo para cada modelo
- [x] Filtros y paginación en transacciones
- [x] Tests unitarios e integración

### 1.4 Importación de Datos ✅
- [x] Endpoint de importación CSV
- [x] Parser para formato OpenBank (investigar formato de exportación)
- [x] Validación y deduplicación de transacciones
- [x] Tests de importación

**Entregable:** API REST funcional con auth, CRUD de cuentas/transacciones/categorías, importación CSV.

---

## FASE 2: Lógica Financiera
**Objetivo:** Cálculos financieros, presupuestos y simulador hipotecario.

### 2.1 Presupuestos ✅
- [x] Modelo Budget
- [x] CRUD de presupuestos mensuales por categoría
- [x] Cálculo de % consumido vs. límite
- [x] Alerta cuando se supera el umbral (almacenar para mostrar en frontend)

### 2.2 Inversiones ✅
- [x] Modelo Investment (depósitos, fondos)
- [x] Registro de depósitos con interés y vencimiento
- [x] Cálculo de rendimiento (simple y compuesto)
- [x] Gestión de renovación de fondos

### 2.3 Analytics ✅
- [x] Endpoint de resumen/overview (ingresos, gastos, ahorro del mes, balance)
- [x] Cash flow mensual (últimos N meses)
- [x] Gastos agrupados por categoría y periodo
- [x] Tasa de ahorro mensual y media móvil
- [x] Tendencias (comparación mes actual vs. anterior, vs. media)

### 2.4 Simulador Hipotecario ✅
- [x] Motor de cálculo: sistema francés de amortización
- [x] Hipoteca tipo fijo: cuota constante
- [x] Hipoteca tipo variable: Euríbor + diferencial, revisión anual/semestral
- [x] Hipoteca mixta: periodo fijo inicial + variable
- [x] Tabla de amortización completa
- [x] Cálculo de máxima hipoteca permitida (regla 30-35% ingresos netos)
- [x] Gastos asociados: notaría, registro, ITP/AJD, gestoría, tasación
- [x] Comparador de escenarios (fijo vs variable vs mixto)

### 2.5 Fiscalidad ✅
- [x] Modelo TaxBracket (tramos IRPF sistema) + TaxConfig (configuración por usuario/año)
- [x] Cálculo bruto → neto (IRPF + Seguridad Social): SS 6.35%/6.50% según año, reducción trabajo 2.000€, mínimo personal 5.550€
- [x] Seed con tramos IRPF vigentes 2025/2026 (escala general y ahorro)
- [x] Integración con simulador hipotecario: parámetro `tax_config_id` en `/mortgage/affordability`

**Entregable:** Motor financiero completo con presupuestos, simulador hipotecario avanzado y analytics.

---

## FASE 3: ML Service - Categorización Automática
**Objetivo:** Servicio de IA para categorización automática de transacciones.

### 3.1 Infraestructura ML ✅
- [x] Crear microservicio ml-service con FastAPI
- [x] Dockerfile con soporte CUDA (nvidia/cuda base image)
- [x] Configurar acceso GPU en docker-compose (nvidia runtime)
- [x] Comunicación backend ↔ ml-service via HTTP interno

### 3.2 Categorización ✅
- [x] Descargar y preparar DistilBERT multilingüe (`distilbert-base-multilingual-cased`)
- [x] Crear dataset sintético de transacciones bancarias españolas (`ml-service/data/synthetic_dataset.py`, 250 ejemplos, 10 categorías)
- [x] Pipeline de preprocessing (`ml-service/app/ml/preprocessor.py`: normalizar referencias, fechas, ruido)
- [x] Fine-tuning del modelo con dataset inicial (`ml-service/scripts/train.py`)
- [x] API de inferencia: POST /predict con descripción → categoría + confianza (`ml-service/app/ml/model_manager.py`)
- [x] Lógica de umbral: auto-asignar si confianza > 0.85, sugerir si > 0.5 (configurable en `ml-service/app/config.py`)
- [x] Endpoint de feedback: usuario confirma/corrige → almacenar en Redis `ml:feedback` para retraining
- [x] Integración automática en `POST /transactions` del backend: auto-asigna o sugiere categoría vía ML

### 3.3 Reentrenamiento Automático
- [ ] Celery task para reentrenamiento incremental
- [ ] Celery Beat: programar reentrenamiento semanal (o cuando haya N correcciones)
- [ ] Versionado de modelos (guardar métricas, rollback si empeora)
- [ ] Endpoint de estado del modelo (accuracy, última fecha de training)

**Entregable:** Categorización automática funcional con feedback loop y reentrenamiento.

---

## FASE 4: ML Service - Predicciones y Escenarios
**Objetivo:** Modelos predictivos y motor de escenarios "what-if".

### 4.1 Predicción de Flujo de Caja
- [ ] Preparar dataset temporal (series mensuales de ingresos/gastos por categoría)
- [ ] Implementar modelo LSTM bidireccional con PyTorch
- [ ] Implementar modelo Prophet como baseline
- [ ] Comparar modelos y seleccionar el mejor (o ensemble)
- [ ] API: predicción de ingresos/gastos para los próximos N meses
- [ ] Intervalos de confianza en las predicciones
- [ ] Reentrenamiento automático mensual

### 4.2 Motor de Escenarios
- [ ] Motor de reglas parametrizable:
  - Variación de sueldo (±X%)
  - Variación de Euríbor
  - Añadir/eliminar gasto recurrente
  - Cambio de tipo impositivo
- [ ] Simulación Monte Carlo para escenarios con incertidumbre
- [ ] Cálculo del impacto fiscal (IRPF) en cada escenario
- [ ] API: POST con parámetros base + modificaciones → resultado con distribución

### 4.3 Predicción de Máxima Hipoteca con IA
- [ ] Combinar predicción de ingresos futuros + escenarios de tipos
- [ ] Calcular capacidad de endeudamiento a X años vista
- [ ] Stress test: "¿podré pagar si el Euríbor sube al 5%?"

**Entregable:** Predicciones de cashflow, análisis de escenarios what-if y asesor hipotecario inteligente.

---

## FASE 5: Frontend - Dashboard
**Objetivo:** Interfaz web completa con SvelteKit.

### 5.1 Setup
- [ ] Crear proyecto SvelteKit con TypeScript
- [ ] Configurar Skeleton UI (tema oscuro por defecto)
- [ ] Cliente API (fetch wrapper con auth, interceptors)
- [ ] Layout principal: sidebar + header + content area
- [ ] Ruteo y guards de autenticación
- [ ] Página de login

### 5.2 Dashboard Principal
- [ ] KPIs cards: balance total, ingresos/gastos del mes, tasa de ahorro
- [ ] Gráfico de evolución de balance (línea temporal)
- [ ] Gráfico de gastos por categoría (donut/pie)
- [ ] Gráfico de cash flow mensual (barras ingresos vs gastos)
- [ ] Alertas de presupuesto activas
- [ ] Widget de últimas transacciones

### 5.3 Gestión de Transacciones
- [ ] Tabla con filtros (fecha, categoría, tipo, cuenta)
- [ ] Formulario de nueva transacción (con sugerencia de categoría IA)
- [ ] Importación CSV con preview y mapeo de columnas
- [ ] Edición inline de categoría (feedback al modelo)
- [ ] Indicador visual de categorización IA vs manual

### 5.4 Presupuestos
- [ ] Vista mensual con barras de progreso por categoría
- [ ] Formulario de creación/edición de presupuesto
- [ ] Comparativa mes actual vs. meses anteriores

### 5.5 Inversiones
- [ ] Lista de depósitos/fondos con rendimiento
- [ ] Timeline de vencimientos
- [ ] Resumen de rendimiento total

### 5.6 Simulador Hipotecario
- [ ] Formulario interactivo (precio, entrada, tipo, plazo)
- [ ] Tabla de amortización con gráfico
- [ ] Comparador visual fijo vs variable vs mixto
- [ ] Slider de Euríbor para ver impacto en tiempo real
- [ ] Capacidad máxima de hipoteca basada en tus datos reales

### 5.7 Predicciones y Escenarios
- [ ] Gráfico de predicción de cashflow (con bandas de confianza)
- [ ] Formulario de "¿qué pasa si...?" con sliders
- [ ] Resultados del escenario vs. situación actual
- [ ] Estado y métricas de los modelos ML

### 5.8 Configuración
- [ ] Perfil de usuario
- [ ] Gestión de categorías
- [ ] Configuración fiscal (tramos IRPF)
- [ ] Tema claro/oscuro
- [ ] Exportación de datos

**Entregable:** Aplicación web completa con todas las vistas y funcionalidades integradas.

---

## FASE 6: Pulido y Producción
**Objetivo:** Preparar para uso diario estable.

### 6.1 Infraestructura
- [ ] Nginx como reverse proxy con SSL local (mkcert)
- [ ] Backups automáticos de PostgreSQL (pg_dump + cron en Docker)
- [ ] Health checks en todos los contenedores
- [ ] docker-compose.yml de producción optimizado
- [ ] Documentación de despliegue

### 6.2 Calidad
- [ ] Coverage de tests > 80% backend
- [ ] Tests E2E frontend (Playwright)
- [ ] Linter + formatter (Ruff para Python, ESLint + Prettier para Svelte)
- [ ] CI con GitHub Actions (tests + lint)

### 6.3 Documentación
- [ ] README completo con screenshots
- [ ] Guía de instalación paso a paso
- [ ] Documentación API (auto-generada por FastAPI + complementos)
- [ ] CONTRIBUTING.md para open source
- [ ] LICENSE (MIT o Apache 2.0)

### 6.4 Mejoras UX
- [ ] Responsive design (tablet/móvil)
- [ ] PWA para acceso desde móvil
- [ ] Notificaciones push (presupuesto superado)
- [ ] Onboarding wizard (primera configuración)

**Entregable:** Aplicación lista para uso diario, documentada y publicable como open source.

---

## FASE 7: Futuro (Post-MVP)
**Ideas para evolución:**

- [ ] Open Banking API: conexión directa con OpenBank para importar transacciones automáticamente
- [ ] Multi-usuario: roles (admin, viewer), compartir dashboards
- [ ] App móvil nativa (React Native o capacitor desde SvelteKit)
- [ ] Alertas por Telegram/email
- [ ] Integración con datos macro (INE, BCE) para predicciones más precisas
- [ ] OCR de tickets/facturas para registro automático
- [ ] Planificación de jubilación
- [ ] Gestión de impuestos (declaración de la renta)
- [ ] API pública para integraciones externas

---

## Dependencias entre Fases

```
FASE 1 (Backend Core)
  │
  ├──► FASE 2 (Lógica Financiera)
  │       │
  │       ├──► FASE 3 (ML Categorización)
  │       │       │
  │       │       └──► FASE 4 (ML Predicciones)
  │       │
  │       └──► FASE 5 (Frontend) ◄── puede empezar en paralelo con Fase 3
  │
  └──► FASE 6 (Pulido) ◄── cuando Fases 1-5 estén completas
```

> **Nota:** La Fase 5 (Frontend) puede comenzarse en paralelo con las Fases 3-4 usando datos mock,
> e ir integrando los endpoints reales conforme estén disponibles.
