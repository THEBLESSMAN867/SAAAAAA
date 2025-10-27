# JSON Schemas for Producer Artifacts
**Updated:** 2025-10-27  
**Validation Level:** Draft-07 (strict)  
**Schema Files Present:** 32

This directory hosts the canonical JSON Schemas consumed by the policy analysis
pipeline. Every schema listed here is curated to support deterministic
validation inside the `choreographer` execution engine and the `report_assembly`
aggregator.

For a producer-by-producer breakdown that `choreographer` can use to resolve
artifact contracts, see
[`CHOREOGRAPHER_SCHEMA_INVENTORY.md`](CHOREOGRAPHER_SCHEMA_INVENTORY.md).

---

## 📁 Directory Structure

```
schemas/
├── CHOREOGRAPHER_SCHEMA_INVENTORY.md   # Exhaustive mapping per producer
├── README.md                           # This file
├── analyzer_one/
│   ├── performance_analysis.schema.json
│   └── semantic_cube.schema.json
├── contradiction_deteccion/
│   ├── contradiction_evidence.schema.json
│   └── policy_statement.schema.json
├── dereck_beach/
│   ├── audit_result.schema.json
│   └── meta_node.schema.json
├── embedding_policy/
│   ├── bayesian_evaluation.schema.json
│   └── semantic_chunk.schema.json
├── execution_mapping.schema.json
├── execution_step.schema.json
├── financiero_viabilidad/
│   ├── causal_dag.schema.json
│   ├── causal_edge.schema.json
│   ├── causal_effect.schema.json
│   ├── causal_node.schema.json
│   ├── counterfactual_scenario.schema.json
│   ├── extracted_table.schema.json
│   ├── financial_indicator.schema.json
│   ├── quality_score.schema.json
│   └── responsible_entity.schema.json
├── policy_processor/
│   └── evidence_bundle.schema.json
├── question_segmentation.schema.json
├── questionnaire.schema.json
├── report_assembly/
│   ├── macro_convergence.schema.json
│   ├── meso_cluster.schema.json
│   └── micro_answer.schema.json
├── rubric.schema.json
├── rubric_scoring.schema.json
├── semantic_chunking_policy/
│   ├── analysis_result.schema.json
│   └── chunk.schema.json
└── teoria_cambio/
    ├── advanced_graph_node.schema.json
    ├── monte_carlo_result.schema.json
    └── validacion_resultado.schema.json
```

> **Note:** All expected schema packages for producer modules are now present and validated.

---

## ✅ Completed Producer Coverage

| Producer Module                     | Primary Schemas                                                                           | Coverage Notes |
|------------------------------------|-------------------------------------------------------------------------------------------|----------------|
| `financiero_viabilidad_tablas.py`  | `causal_node`, `causal_edge`, `causal_dag`, `causal_effect`, `financial_indicator`, `counterfactual_scenario`, `extracted_table`, `responsible_entity`, `quality_score` | Complete       |
| `contradiction_deteccion.py`       | `policy_statement`, `contradiction_evidence`                                              | Complete       |
| `dereck_beach.py`                  | `meta_node`, `audit_result`                                                               | Complete       |
| `embedding_policy.py`              | `semantic_chunk`, `bayesian_evaluation`                                                   | Complete       |
| `teoria_cambio.py`                 | `advanced_graph_node`, `validacion_resultado`, `monte_carlo_result`                       | Complete       |
| `report_assembly.py`               | `micro_answer`, `meso_cluster`, `macro_convergence`                                        | Complete       |
| `Analyzer_one.py`                  | `semantic_cube`, `performance_analysis`                                                    | Complete       |
| `policy_processor.py`              | `evidence_bundle`                                                                          | Complete       |
| `semantic_chunking_policy.py`      | `chunk`, `analysis_result`                                                                 | Complete       |

---

## 🎉 All Producer Schemas Complete

All expected schemas for the nine producer modules have been authored and validated against JSON Schema Draft-07 specification. The schema inventory is now complete and ready for choreographer integration.

---

## 🎯 Validation Usage

Schemas follow JSON Schema Draft-07. Validation pipelines should enable
`additionalProperties: false` enforcement and strict type checking. Example in
Python:

```python
import json
import jsonschema
from pathlib import Path

schema = json.loads(Path("schemas/financiero_viabilidad/causal_node.schema.json").read_text())
instance = {
    "name": "Infraestructura y adecuación de tierras",
    "node_type": "pilar",
    "embedding": None,
    "associated_budget": "500000000.00",
    "temporal_lag": 2,
    "evidence_strength": 0.85
}

jsonschema.validate(instance=instance, schema=schema)
```

For CLI validation use `ajv` with `--strict` mode to mirror production checks.
