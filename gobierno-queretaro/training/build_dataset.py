"""
Gobierno Querétaro - Dataset Builder
Extract training/validation datasets from collected agent-lightning traces.

Usage:
    python -m training.build_dataset --output-dir ./training/datasets

Reads from the LightningStore (in-memory or persistent) and produces
structured datasets for APO and RL training.
"""

import argparse
import json
import logging
from pathlib import Path

from agentlightning.agent import find_reward_spans, get_message_value, get_reward_value
from agentlightning.store import InMemoryLightningStore

# Import the keyword map as ground truth for synthetic bootstrap data
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator.classifier import KEYWORD_MAP

logger = logging.getLogger(__name__)


def build_classifier_dataset_from_traces(store: InMemoryLightningStore) -> tuple[list, list]:
    """
    Build classifier training/validation dataset from collected traces.

    Each example:
        {
            "message": str,          # Citizen message
            "context": str | None,   # Conversation context
            "expected_category": str, # Ground truth category
            "reward": float,         # Quality signal from auto-heuristics + human feedback
            "method": str,           # How the category was determined
        }

    Returns:
        (train_examples, val_examples) split 70/30
    """
    examples = []

    spans = store.query_spans()
    for span in spans:
        # Look for classification annotation spans
        attrs = span.get("attributes", {})
        category = attrs.get("classification.category")
        if not category:
            continue

        # Find associated message and reward
        message = attrs.get("message.content", "")
        method = attrs.get("classification.method", "unknown")
        confidence = float(attrs.get("classification.confidence", 0))

        # Find reward spans associated with this trace
        reward = 0.0
        reward_spans = find_reward_spans(span.get("children", []))
        for rs in reward_spans:
            reward += get_reward_value(rs) or 0.0

        examples.append({
            "message": message,
            "context": attrs.get("conversation.context"),
            "expected_category": category,
            "reward": reward,
            "confidence": confidence,
            "method": method,
        })

    # Split 70/30
    split_idx = int(len(examples) * 0.7)
    return examples[:split_idx], examples[split_idx:]


def build_synthetic_classifier_dataset() -> tuple[list, list]:
    """
    Build a synthetic classifier dataset from KEYWORD_MAP for bootstrapping.

    Uses the keyword map as ground truth to generate synthetic examples
    before enough production traces are collected.

    Returns:
        (train_examples, val_examples)
    """
    examples = []

    # Generate examples from keyword patterns
    category_templates = {
        "CEA": [
            "Tengo una fuga de agua en mi casa",
            "¿Cuánto debo de agua?",
            "Necesito reconexión del servicio de agua",
            "Mi medidor está roto",
            "No hay agua en mi colonia",
            "Quiero aclarar mi recibo de agua",
            "El drenaje está tapado en mi calle",
        ],
        "TRA": [
            "¿Qué ruta de camión pasa por el centro?",
            "¿Cuál es el horario del autobús 25?",
            "Quiero recargar mi tarjeta de transporte",
            "¿Cómo llego a Juriquilla en camión?",
            "La parada del camión no tiene techo",
        ],
        "EDU": [
            "¿Cuándo son las inscripciones para primaria?",
            "Necesito una constancia escolar de mi hijo",
            "¿Hay becas disponibles para preparatoria?",
            "Quiero información sobre preinscripción",
        ],
        "VEH": [
            "¿Cómo pago la tenencia de mi carro?",
            "Tengo una multa de tránsito, ¿cómo la pago?",
            "Necesito renovar mis placas",
            "¿Dónde saco la licencia de conducir?",
            "Se me perdió la placa de mi carro",
        ],
        "PSI": [
            "Necesito una cita con psicólogo",
            "Estoy pasando por una depresión",
            "¿Tienen servicio de apoyo emocional?",
            "Busco ayuda para mi ansiedad",
        ],
        "IQM": [
            "Sufro violencia doméstica, ¿a dónde acudo?",
            "Necesito asesoría legal como mujer",
            "¿Dónde puedo denunciar acoso?",
            "Busco refugio para mujeres",
        ],
        "CUL": [
            "¿Qué eventos culturales hay este mes?",
            "¿Cuál es el horario del museo de la ciudad?",
            "Quiero inscribirme a un taller de pintura",
            "¿Hay becas para artistas?",
        ],
        "RPP": [
            "Necesito un certificado de libertad de gravamen",
            "¿Cómo consulto mi propiedad en el registro?",
            "Quiero cancelar una hipoteca en el registro",
            "Necesito copias certificadas de una escritura",
        ],
        "LAB": [
            "Me despidieron injustamente, ¿qué hago?",
            "Quiero poner una demanda laboral",
            "¿Cómo calculo mi finiquito?",
            "Necesito asesoría sobre mis derechos laborales",
        ],
        "VIV": [
            "¿Cómo solicito un crédito de vivienda?",
            "Quiero escriturar mi casa con IVEQ",
            "¿Hay programas de vivienda disponibles?",
            "Necesito regularizar mi terreno",
        ],
        "APP": [
            "La aplicación del gobierno no funciona",
            "¿Cómo descargo la app de APPQRO?",
            "Me sale un error en la app",
            "No puedo iniciar sesión en la aplicación",
        ],
        "SOC": [
            "¿Qué programas sociales hay disponibles?",
            "Tengo problemas con mi tarjeta Contigo",
            "¿Cómo solicito un apoyo económico?",
            "¿Hay despensas disponibles?",
        ],
        "ATC": [
            "Quiero poner una queja",
            "¿Cómo me comunico con atención ciudadana?",
            "Tengo una sugerencia para el gobierno",
            "No sé a quién acudir con mi problema",
        ],
        "EXIT": [
            "Gracias, eso es todo",
            "Adiós, muchas gracias",
            "Ya no necesito nada más",
            "Bye, gracias por la ayuda",
        ],
    }

    for category, messages in category_templates.items():
        for msg in messages:
            examples.append({
                "message": msg,
                "context": None,
                "expected_category": category,
                "reward": 1.0,  # Ground truth → perfect reward
                "confidence": 1.0,
                "method": "synthetic",
            })

    # Shuffle deterministically
    import hashlib
    examples.sort(key=lambda x: hashlib.md5(x["message"].encode()).hexdigest())

    split_idx = int(len(examples) * 0.7)
    return examples[:split_idx], examples[split_idx:]


def save_dataset(examples: list, output_path: Path):
    """Save dataset to JSONL format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
    logger.info(f"Saved {len(examples)} examples to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build training datasets")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./training/datasets",
        help="Output directory for datasets",
    )
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Generate only synthetic dataset (no traces needed)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    output_dir = Path(args.output_dir)

    # Always generate synthetic dataset for bootstrapping
    train_syn, val_syn = build_synthetic_classifier_dataset()
    save_dataset(train_syn, output_dir / "classifier_train_synthetic.jsonl")
    save_dataset(val_syn, output_dir / "classifier_val_synthetic.jsonl")
    logger.info(
        f"Synthetic dataset: {len(train_syn)} train, {len(val_syn)} val examples"
    )


if __name__ == "__main__":
    main()
