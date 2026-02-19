#!/usr/bin/env python3
"""
Interactive CLI for testing Gobierno Querétaro agents locally.
Run: python scripts/test-cli.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.classifier import classify_message, CATEGORIES

def print_banner():
    print("\n" + "=" * 60)
    print("  Gobierno Querétaro - Agentes de Servicio Ciudadano")
    print("  Modo de Prueba Interactivo")
    print("=" * 60)
    print("\nCategorías disponibles:")
    for code, info in CATEGORIES.items():
        print(f"  {code}: {info['name']}")
    print("\nEscribe tu mensaje o 'salir' para terminar.\n")

def main():
    print_banner()

    while True:
        try:
            message = input("Ciudadano> ").strip()

            if not message:
                continue

            if message.lower() in ['salir', 'exit', 'quit', 'q']:
                print("\n¡Gracias por usar el servicio! Hasta pronto.")
                break

            # Classify the message
            category = classify_message(message)
            category_info = CATEGORIES.get(category, CATEGORIES["ATC"])

            print(f"\n📍 Clasificación: {category} - {category_info['name']}")
            print(f"🔗 Agente asignado: {category_info.get('agent', 'agent-citizen-attention')}")

            # Simulate agent response based on category
            responses = {
                "CEA": "🚰 Conectando con Agente de Agua CEA...\n   Para consultar tu saldo, necesito tu número de contrato.",
                "TRA": "🚌 Conectando con Agente de Transporte AMEQ...\n   ¿Qué ruta o información de transporte necesitas?",
                "EDU": "📚 Conectando con Agente de Educación USEBEQ...\n   ¿Qué información escolar necesitas?",
                "VEH": "🚗 Conectando con Agente de Vehículos...\n   ¿Necesitas información sobre placas, multas o licencias?",
                "PSI": "💚 Conectando con Agente de Psicología SEJUVE...\n   Estamos aquí para ayudarte. ¿Cómo te sientes?",
                "IQM": "💜 Conectando con Instituto Queretano de la Mujer...\n   Estás en un espacio seguro. ¿Cómo podemos ayudarte?",
                "CUL": "🎭 Conectando con Agente de Cultura...\n   ¿Qué eventos o talleres te interesan?",
                "RPP": "📋 Conectando con Registro Público de la Propiedad...\n   ¿Qué documento o certificado necesitas?",
                "LAB": "⚖️ Conectando con Centro de Conciliación Laboral...\n   ¿Tienes un problema laboral que reportar?",
                "VIV": "🏠 Conectando con Agente de Vivienda IVEQ...\n   ¿Buscas información sobre créditos o programas de vivienda?",
                "APP": "📱 Conectando con Soporte de APPQRO...\n   ¿Qué problema tienes con la aplicación?",
                "SOC": "🤝 Conectando con Programas Sociales SEDESOQ...\n   ¿Qué programa o apoyo te interesa?",
                "ATC": "📞 Conectando con Atención Ciudadana...\n   ¿Cómo podemos ayudarte hoy?",
            }

            print(f"\n{responses.get(category, responses['ATC'])}")
            print("-" * 40 + "\n")

        except KeyboardInterrupt:
            print("\n\n¡Hasta pronto!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")

if __name__ == "__main__":
    main()
