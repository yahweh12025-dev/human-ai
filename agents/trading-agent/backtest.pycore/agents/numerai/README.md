# Numerai Agent

Numerai ML pipeline integrated into the Human-AI swarm. Trains a LightGBM model on
Numerai's obfuscated stock-market dataset and optionally submits live predictions to
the Numerai tournament.

## Quick Start

```bash
# From the human-ai project root
source .venv/bin/activate

# Dry-run (no API key needed — uses synthetic data if nothing is cached)
python3 agents/numerai/numerai_pipeline.py --dry-run

# Full run with submission
python3 agents/numerai/numerai_pipeline.py --model-id <your_model_id>
```

## Getting an API Key

1. Create an account at https://numer.ai/
2. Navigate to **Account > API Keys** and generate a new key pair.
3. Create a model at **numer.ai/models** and copy the Model ID.
4. Add credentials to `.env` in the project root:

```env
NUMERAI_PUBLIC_ID=your_public_id_here
NUMERAI_SECRET_KEY=your_secret_key_here
```

The pipeline reads `.env` automatically — no extra steps needed.

## CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--dry-run` | off | Skip submission; use synthetic data if no cache |
| `--model-id` | (empty) | Numerai model ID for live submission |
| `--feature-set` | `small` | Feature set: `small` (42), `medium` (780), `all` (2748) |
| `--data-version` | `v5.2` | Numerai dataset version |

## Data & Logs

- Downloaded data: `data/numerai/v5.2/`
- Pipeline log: `data/logs/numerai.log`

## Features Engineered

On top of Numerai's base features the pipeline derives:
- **RSI** (14-period) on pilot features
- **EMA slope** (10-period) on pilot features
- **Bollinger Band width** (10-period) on pilot features
- **Volume proxy**: mean absolute deviation from neutral value across pilot features
- **ATR proxy**: cross-sectional std across pilot features

## Tournament Context

The Numerai tournament evaluates models on **CORR** (Pearson correlation with target)
and **MMC** (Meta Model Contribution — uniqueness to the crowd). New live features
drop Tuesday–Saturday; submissions are scored 20 business days later.

See the example notebooks in `agents/numerai/example-scripts/numerai/` for deeper
exploration of the dataset and scoring mechanics.
