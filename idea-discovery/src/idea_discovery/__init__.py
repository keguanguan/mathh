"""idea_discovery: pipeline for measuring mathematical idea discovery in LMs.

Package layout (see README.md):
    structures/   abstract mathematical structures shared by families and verifiers
    families/     ProblemFamily implementations (instance generation, rendering, ground truth)
    certificates/ certificate schemas and parsing of model-produced certificates
    verifiers/    deterministic certificate verifiers (structure + decision relevance)
    generation/   instance-set and transfer-instance generation from configs
    prompting/    prompt construction for the free-solve / post-hoc / supplied-idea protocol
    models/       ModelRunner adapters (mock, real providers)
    extraction/   candidate-certificate extraction from free responses
    evaluation/   trial execution and raw-record logging
    analysis/     tidy tables, metrics I(n), S(n), ..., figures
    utils/        serialization, hashing, safe expression evaluation, statistics
"""

__version__ = "0.1.0"
