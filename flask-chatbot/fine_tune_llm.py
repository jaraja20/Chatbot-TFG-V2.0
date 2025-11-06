"""
Fine-tuning de llama-3.2-1b para clasificación de intents
Usando unsloth para mayor velocidad y eficiencia
"""

import torch
from datasets import load_dataset
import os

print("🚀 Iniciando Fine-tuning de llama-3.2-1b")
print("=" * 60)

# =====================================================
# PASO 1: Verificar GPU/CPU
# =====================================================
if torch.cuda.is_available():
    print(f"✅ GPU disponible: {torch.cuda.get_device_name(0)}")
    device = "cuda"
else:
    print("⚠️ GPU no disponible, usando CPU (será más lento)")
    device = "cpu"

# =====================================================
# PASO 2: Cargar modelo base
# =====================================================
print("\n📥 Cargando modelo base...")

# Usamos TinyLlama: open-source, ~1B parámetros, no requiere autenticación
# Alternativas: microsoft/phi-2 (2.7B), distilgpt2 (small)
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

try:
    from unsloth import FastLanguageModel
    
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_NAME,
        max_seq_length = 512,
        dtype = None,  # Auto-detecta
        load_in_4bit = True,  # Usa quantización 4-bit para ahorrar memoria
    )
    print(f"✅ Modelo {MODEL_NAME} cargado con unsloth (optimizado)")
    
except ImportError:
    print("⚠️ unsloth no disponible, usando transformers estándar")
    from transformers import AutoModelForCausalLM, AutoTokenizer
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    print(f"✅ Modelo {MODEL_NAME} cargado con transformers")

# =====================================================
# PASO 3: Preparar modelo para fine-tuning (LoRA)
# =====================================================
print("\n🔧 Configurando LoRA para fine-tuning eficiente...")

try:
    from peft import LoraConfig, get_peft_model, TaskType
    
    # Configuración LoRA (Low-Rank Adaptation)
    lora_config = LoraConfig(
        r=16,  # Rango de la matriz LoRA
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )
    
    model = get_peft_model(model, lora_config)
    print("✅ LoRA configurado (solo entrena ~1% de parámetros)")
    
except ImportError:
    print("⚠️ PEFT no disponible, fine-tuning completo (más lento)")

# =====================================================
# PASO 4: Cargar dataset
# =====================================================
print("\n📊 Cargando dataset de training...")

train_dataset = load_dataset('json', data_files='dataset_training_filtered.jsonl', split='train')
val_dataset = load_dataset('json', data_files='dataset_validation.jsonl', split='train')

print(f"✅ Training: {len(train_dataset)} ejemplos")
print(f"✅ Validation: {len(val_dataset)} ejemplos")

# =====================================================
# PASO 5: Configurar training
# =====================================================
print("\n⚙️ Configurando parámetros de training...")

from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    output_dir="./llama-3.2-1b-intent-classifier",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,
    warmup_steps=10,
    learning_rate=2e-4,
    fp16=True if device == "cuda" else False,
    logging_steps=5,
    eval_strategy="steps",
    eval_steps=10,
    save_steps=20,
    save_total_limit=2,
    load_best_model_at_end=True,
    report_to="none",  # No usar wandb/tensorboard
)

# =====================================================
# PASO 6: Función de formateo de datos
# =====================================================
def format_prompts(examples):
    texts = []
    for messages in examples["messages"]:
        # Convertir formato messages a texto
        text = ""
        for msg in messages:
            if msg["role"] == "system":
                text += f"<|system|>\n{msg['content']}\n"
            elif msg["role"] == "user":
                text += f"<|user|>\n{msg['content']}\n"
            elif msg["role"] == "assistant":
                text += f"<|assistant|>\n{msg['content']}\n"
        texts.append(text)
    
    return tokenizer(texts, truncation=True, padding="max_length", max_length=512)

# Aplicar formateo
train_dataset = train_dataset.map(format_prompts, batched=True, remove_columns=train_dataset.column_names)
val_dataset = val_dataset.map(format_prompts, batched=True, remove_columns=val_dataset.column_names)

# =====================================================
# PASO 7: Crear trainer
# =====================================================
print("\n🏋️ Creando trainer...")

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
)

# =====================================================
# PASO 8: Entrenar!
# =====================================================
print("\n🚀 Iniciando training...")
print("=" * 60)
print("⏰ Esto tomará aproximadamente 30-60 minutos según tu hardware")
print("=" * 60)

trainer.train()

# =====================================================
# PASO 9: Guardar modelo
# =====================================================
print("\n💾 Guardando modelo fine-tuned...")

OUTPUT_DIR = "./tinyllama-intent-classifier-final"
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"✅ Modelo guardado en: {OUTPUT_DIR}")

# =====================================================
# PASO 10: Evaluar
# =====================================================
print("\n📊 Evaluando modelo en validation set...")

eval_results = trainer.evaluate()
print(f"\n📈 Resultados de evaluación:")
for key, value in eval_results.items():
    print(f"   {key}: {value:.4f}")

print("\n" + "=" * 60)
print("🎉 FINE-TUNING COMPLETADO!")
print("=" * 60)
print(f"✅ Modelo entrenado guardado en: llama-3.2-1b-intent-classifier-final")
print(f"✅ Listo para integrar en orquestador_inteligente.py")
