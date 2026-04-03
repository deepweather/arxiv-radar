"""Application-wide constants. Tunable values that aren't user-facing settings."""

BCRYPT_ROUNDS = 12

MIN_SUBMIT_SECONDS = 2

# Reciprocal Rank Fusion constant for hybrid search
RRF_K = 60

# pgvector HNSW index parameters
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 64
