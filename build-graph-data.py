#!/usr/bin/env python3
"""Convert loom-nodes.json → graph-data.json for the split-screen explorer UI.

Outputs Ael-compatible format:
  nodes: [{id, type, summary, skeleton, origin, source_notes}]
  edges: [{source, target, predicate, weight, source_note}]
  communities: {"0": [member_ids], "1": [...]}
"""

import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import random

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

LOOM_NODES = Path(os.path.expanduser(
    "~/autonomous-ai/connection-map-public/docs/loom-nodes.json"
))
ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
OUTPUT = DOCS / "graph-data.json"

CLUSTER_THRESHOLD = 0.60


def label_propagation(adj, node_ids, seed=42):
    labels = {nid: i for i, nid in enumerate(node_ids)}
    rng = random.Random(seed)

    for _ in range(30):
        changed = False
        order = list(node_ids)
        rng.shuffle(order)
        for nid in order:
            neighbors = adj.get(nid, set())
            if not neighbors:
                continue
            neighbor_labels = [labels[nb] for nb in neighbors if nb in labels]
            if not neighbor_labels:
                continue
            counts = Counter(neighbor_labels)
            max_count = counts.most_common(1)[0][1]
            tied = [lbl for lbl, c in counts.items() if c == max_count]
            best = labels[nid] if labels[nid] in tied else min(tied)
            if labels[nid] != best:
                labels[nid] = best
                changed = True
        if not changed:
            break

    return labels


def main():
    with open(LOOM_NODES) as f:
        source = json.load(f)

    nodes_raw = source["nodes"]
    edges_raw = source["curated_edges"]
    id_set = {n["id"] for n in nodes_raw}
    print(f"Loaded {len(nodes_raw)} nodes, {len(edges_raw)} curated edges")

    # Extract embeddings for similarity edges
    valid_ids = []
    emb_list = []
    for n in nodes_raw:
        if n.get("embedding"):
            emb_list.append(n["embedding"])
            valid_ids.append(n["id"])
    embeddings = np.array(emb_list) if emb_list else np.array([])
    print(f"  {len(valid_ids)} nodes with embeddings")

    # Compute cosine similarity matrix
    sim = None
    if len(embeddings) > 0:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normed = embeddings / norms
        sim = normed @ normed.T

    # Build edges from curated
    edges = []
    for e in edges_raw:
        src = e.get("source")
        tgt = e.get("target")
        if src in id_set and tgt in id_set:
            edges.append({
                "source": src,
                "target": tgt,
                "predicate": e.get("predicate", "related_to"),
                "weight": 1.0,
                "source_note": e.get("source_note", ""),
            })
    curated_count = len(edges)

    # Add cosine similarity edges
    curated_pairs = {(e["source"], e["target"]) for e in edges}
    curated_pairs |= {(e["target"], e["source"]) for e in edges}

    if sim is not None:
        threshold = 0.70
        added = 0
        for i in range(len(valid_ids)):
            for j in range(i + 1, len(valid_ids)):
                score = float(sim[i, j])
                if score >= threshold and (valid_ids[i], valid_ids[j]) not in curated_pairs:
                    edges.append({
                        "source": valid_ids[i],
                        "target": valid_ids[j],
                        "predicate": "cosine_similarity",
                        "weight": round(score, 3),
                        "source_note": "",
                    })
                    added += 1
        print(f"  Curated: {curated_count}, Semantic (>={threshold}): {added}, Total: {len(edges)}")

    # Community detection via label propagation (curated edges only)
    adj = defaultdict(set)
    for e in edges:
        if e.get("predicate") == "cosine_similarity":
            continue
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])

    node_ids = [n["id"] for n in nodes_raw]
    labels = label_propagation(adj, node_ids)

    community_members = defaultdict(list)
    for nid, label in labels.items():
        community_members[label].append(nid)
    ranked = sorted(community_members.items(), key=lambda x: -len(x[1]))
    remap = {old_id: new_id for new_id, (old_id, _) in enumerate(ranked)}

    communities = {}
    for old_id, members in community_members.items():
        communities[str(remap[old_id])] = members

    # Build nodes in Ael-compatible format
    nodes = []
    for n in nodes_raw:
        summary = n.get("summary", "")
        skeleton = n.get("skeleton") or (summary[:120] + ("..." if len(summary) > 120 else ""))
        url = n.get("url") or n.get("source_url") or ""
        nodes.append({
            "id": n["id"],
            "type": n.get("type", "concept"),
            "summary": summary,
            "skeleton": skeleton,
            "origin": n.get("origin", "loom"),
            "source_notes": [url] if url else [],
        })

    data = {
        "nodes": nodes,
        "edges": edges,
        "communities": communities,
    }

    os.makedirs(DOCS, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nBuilt {OUTPUT}: {len(nodes)} nodes, {len(edges)} edges, {len(communities)} communities")


if __name__ == "__main__":
    main()
