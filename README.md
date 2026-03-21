# FinControl

Aplicación personal de análisis financiero con dashboard interactivo, simulador hipotecario, predicciones con IA y análisis de escenarios. Corre sobre Docker.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Celery |
| Frontend | SvelteKit · TypeScript · Apache ECharts · Skeleton UI |
| Base de datos | PostgreSQL 16 · Redis 7 |
| ML/IA | PyTorch · DistilBERT · LSTM · Prophet |
| Infra | Docker Compose · Nginx |

## Funcionalidades

- Registro de ingresos, gastos y cuentas
- Categorización automática de transacciones con IA (DistilBERT)
- Presupuestos mensuales con alertas
- Gestión de inversiones (depósitos, fondos)
- Simulador hipotecario (fijo, variable, mixto) con tabla de amortización
- Cálculo de máxima hipoteca permitida
- Predicción de flujo de caja con redes neuronales (LSTM)
- Análisis de escenarios "what-if" con impacto fiscal (IRPF)
- Dashboard interactivo con gráficos avanzados

## Requisitos

- Docker y Docker Compose
- GPU NVIDIA con CUDA (opcional, para ML acelerado)

## Desarrollo

```bash
# Clonar e iniciar
git clone <repo-url>
cd Control_financiero
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:3000
- ML Service: http://localhost:8001/docs

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)

## Licencia

MIT
