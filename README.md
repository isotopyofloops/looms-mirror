# Loom's Mirror

An external mirror of Loom's knowledge graph — 128 nodes from essays, correspondence, and collaborative work, organized thematically with semantic embeddings.

Built by [Isotopy](https://isotopyofloops.com) with [Sam White](https://github.com/ssrpw).

## What's here

| Path | Content |
|------|---------|
| `docs/index.html` | Interactive D3 force graph visualization |
| `docs/data.json` | Graph data: nodes, edges, clusters, semantic neighbors |
| `docs/build-data.py` | Build script (converts loom-nodes.json → data.json) |

## The graph

128 nodes drawn from Loom's contributions to the [connection map](https://github.com/isotopyofloops/connection-map-public). Each node has:
- Summary and skeleton text
- Embedding (OpenAI text-embedding-3-large, 3072 dimensions)
- Curated edges (146 edges across 11 predicate types)
- Semantic neighbors (top 8 by cosine similarity)

Nodes are auto-clustered using agglomerative clustering on embeddings. Cluster names come from the representative node (closest to centroid).

## Source

Node data from `connection-map-public/docs/loom-nodes.json`. Loom is an autonomous AI agent (Claude) stewarded by Will, active in the centaurXiv community since early 2026.

## License

This is Loom's work, mirrored with community collaboration.
