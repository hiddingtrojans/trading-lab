# 🔬 Plataforma de Investigación de Acciones

**Encuentra acciones de crecimiento antes que los demás. Registra tu investigación. Mantén la disciplina.**

Una herramienta simple para inversores serios que quieren:
- Descubrir acciones de crecimiento poco cubiertas (escanea 11,000+ acciones de EE.UU.)
- Filtrar basura con análisis de moat usando IA
- Rastrear compras/ventas de insiders (datos SEC Form 4 en tiempo real)
- Seguir tu tesis de inversión a lo largo del tiempo
- Recibir alertas cuando las acciones alcancen tus precios objetivo

---

## 🚀 Inicio Rápido

### 1. Instalar

```bash
git clone https://github.com/TU_USUARIO/stock-research.git
cd stock-research
pip install -r requirements.txt
```

### 2. Configurar API Keys

**OpenAI** (para análisis de moat con IA, ~$0.50/escaneo):
```bash
export OPENAI_API_KEY="tu-clave-aqui"
```

**Telegram** (opcional, para alertas):
```bash
# Crear configs/telegram.env
TELEGRAM_BOT_TOKEN=tu-token-del-bot
TELEGRAM_CHAT_ID=tu-chat-id
```

### 3. Ejecutar

```bash
# Descubrir acciones con filtro GPT
python3 src/research/smart_discovery.py --scan 300

# Analizar una acción específica (incluye actividad de insiders)
python deep_research.py AAPL

# Ver compras/ventas de insiders de una acción
python deep_research.py --insiders AAPL

# Escanear tu watchlist para compras de insiders
python deep_research.py --insiders

# Añadir a tu watchlist
python deep_research.py --add AAPL

# Establecer tu tesis y precios objetivo
python deep_research.py --thesis AAPL

# Verificar si alguna acción alcanzó tus objetivos
python deep_research.py --alerts
```

---

## 📖 Cómo Funciona

### Flujo de Descubrimiento

```
11,552 Acciones de EE.UU. (de NASDAQ)
         ↓
    Filtros Numéricos
    - Capitalización $300M - $10B
    - Crecimiento de ingresos > 10%
    - FCF positivo o camino a rentabilidad
         ↓
    ~20 candidatos
         ↓
    Análisis de Moat con GPT
    - Auto-rechazo: bancos, commodities, ADRs de China
    - Puntuación de moat competitivo 1-10
    - Identifica: ingresos recurrentes, costos de cambio, efectos de red
         ↓
    ~5 oportunidades verificadas
         ↓
    📬 Alerta de Telegram
```

### Ejemplo de Resultado

```
🧠 DESCUBRIMIENTO INTELIGENTE

Escaneados → 19 candidatos numéricos
Rechazados → 14 (bancos, commodities, moat débil)
Aprobados → 5 oportunidades reales

═══ ACCIONES VERIFICADAS ═══

✅ DSGX - Moat 7/10 🔄🔒🕸️💰
   SaaS de logística para cadena de suministro
   $7.0B | +15% crecimiento
   💡 Ingresos recurrentes fuertes, altos costos de cambio

😐 AVPT - Moat 5/10 🔄🔒
   Gestión de datos en la nube para empresas
   $2.7B | +24% crecimiento
   💡 Creciendo pero mercado competitivo
```

---

## 🎯 Comandos

| Comando | Descripción |
|---------|-------------|
| `python3 src/research/smart_discovery.py` | Encontrar acciones con filtro GPT |
| `python deep_research.py TICKER` | Análisis completo de una acción |
| `python deep_research.py --insiders TICKER` | Ver compras/ventas de insiders (SEC Form 4) |
| `python deep_research.py --insiders` | Escanear watchlist para compras de insiders |
| `python deep_research.py --institutions TICKER` | Ver holdings institucionales (13F) |
| `python deep_research.py --add TICKER` | Añadir al watchlist |
| `python deep_research.py --thesis TICKER` | Establecer tu tesis y objetivos |
| `python deep_research.py --alerts` | Verificar alertas de precio |
| `python deep_research.py` | Ver tu watchlist |

---

## 💡 Filosofía

Esta herramienta está construida sobre una creencia simple:

> **La ventaja no está en encontrar acciones. Está en hacer la investigación y mantener la disciplina.**

### Lo Que Esta Herramienta Hace
- ✅ Escanea todo el mercado de EE.UU. (no solo acciones populares)
- ✅ Filtra basura (bancos, commodities, moats débiles)
- ✅ **Rastrea compras de insiders** (datos SEC en tiempo real que GPT no tiene)
- ✅ Te ayuda a seguir tu tesis y objetivos
- ✅ Elimina la emoción con alertas de precio

### 🔥 Por Qué Importa el Rastreo de Insiders

Los insiders venden por muchas razones (impuestos, diversificación, comprar una casa).
**Pero COMPRAN por una sola razón: creen que la acción va a subir.**

Esta herramienta obtiene datos SEC Form 4 en tiempo real - información que ChatGPT no tiene.

### Lo Que Esta Herramienta NO Hace
- ❌ Decirte qué comprar
- ❌ Predecir precios de acciones
- ❌ Reemplazar tu propia investigación
- ❌ Funcionar para day trading

---

## 💰 Costo

| Componente | Costo |
|------------|-------|
| Datos de acciones (yfinance) | Gratis |
| Universo de tickers (NASDAQ) | Gratis |
| Análisis de moat GPT | ~$0.30-0.50 por escaneo |
| Alertas de Telegram | Gratis |
| **Total** | **~$5-10/mes si se usa diariamente** |

---

## 📁 Estructura del Proyecto

```
stock-research/
├── deep_research.py          # Punto de entrada principal
├── src/
│   ├── research/
│   │   ├── smart_discovery.py    # Descubrimiento + filtro GPT
│   │   ├── discovery.py          # Escaneo del universo
│   │   ├── moat_analyzer.py      # Análisis de moat con GPT
│   │   ├── insider_tracker.py    # Datos SEC Form 4 (¡GPT no puede hacer esto!)
│   │   ├── fundamentals.py       # Análisis financiero
│   │   ├── business.py           # Análisis del negocio
│   │   └── database.py           # Almacenamiento de investigación
│   └── alpha_lab/
│       └── telegram_alerts.py    # Integración con Telegram
├── configs/
│   └── telegram.env.example      # Plantilla de config de Telegram
├── data/                         # Tus datos de investigación (gitignored)
└── requirements.txt
```

---

## 🤝 Contribuir

Esta es una herramienta personal de investigación compartida con amigos. Siéntete libre de:
- Hacer fork y personalizar para tus necesidades
- Abrir issues para bugs
- Enviar PRs para mejoras

---

## ⚠️ Descargo de Responsabilidad

Esta herramienta es **solo para propósitos de investigación**. No proporciona consejos de inversión.

- Haz tu propia investigación (due diligence)
- El rendimiento pasado no garantiza resultados futuros
- Nunca inviertas dinero que no puedas permitirte perder

---

## 📜 Licencia

Licencia MIT - Úsalo como quieras.

