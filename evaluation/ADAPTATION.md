# Adaptation gate

The base-model evaluation is established before adaptation. `specialization_seed.jsonl` contains 12 focused, traceable synthetic development examples; `heldout.jsonl` contains separate adversarial cases. These are seed materials, not a claim that 300–500 high-quality operator-reviewed examples have been completed.

The Liquid baseline's measured hallucinations justify investigating specialization, but do not by themselves justify launching a GPU training job on the shared Jetson. First select the measured model, expand unique examples from approved project evidence, review grounded tool-call transcripts, verify model-specific LoRA support, and keep all source groups disjoint from held-out evaluation. Operator review and the requested 300–500-example curation remain outstanding.

No fine-tuning was launched, no unrelated compute was accessed, and original models were preserved. A generic untested QLoRA YAML would not be a reproducible validated training procedure, so none is presented as such.
