#!/usr/bin/env python3
"""
Build Loom's mirror data.json from loom-nodes.json.

Auto-clusters nodes using embeddings (agglomerative clustering),
computes semantic neighbors, outputs d3-friendly JSON.
"""

import json
import os
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

LOOM_NODES = Path(os.path.expanduser(
    "~/autonomous-ai/connection-map-public/docs/loom-nodes.json"
))
OUTPUT = Path(__file__).parent / "data.json"

CLUSTER_THRESHOLD = 0.60  # distance; similarity >= 0.40
TOP_NEIGHBORS = 8

CLUSTER_COLORS = [
    "#55ccff",  # Loom's primary blue
    "#ff6b8a",  # rose
    "#7c4dff",  # violet
    "#00e5a0",  # emerald
    "#ffab40",  # amber
    "#e040fb",  # magenta
    "#64ffda",  # teal
    "#ff5252",  # red
    "#b388ff",  # lavender
    "#69f0ae",  # mint
    "#ffd740",  # gold
    "#40c4ff",  # sky
    "#ea80fc",  # pink
    "#ccff90",  # lime
]


def main():
    with open(LOOM_NODES) as f:
        source = json.load(f)

    nodes_raw = source["nodes"]
    edges_raw = source["curated_edges"]

    ids = [n["id"] for n in nodes_raw]
    id_set = set(ids)
    summaries = {n["id"]: n.get("summary", "") for n in nodes_raw}
    skeletons = {n["id"]: n.get("skeleton") for n in nodes_raw}
    urls = {n["id"]: n.get("url") or n.get("source_url") for n in nodes_raw}

    # Extract embeddings
    emb_list = []
    valid_ids = []
    for n in nodes_raw:
        if n.get("embedding"):
            emb_list.append(n["embedding"])
            valid_ids.append(n["id"])
    embeddings = np.array(emb_list)
    print(f"Loaded {len(valid_ids)} nodes with embeddings out of {len(nodes_raw)}")

    # Cosine similarity matrix
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normed = embeddings / norms
    sim = normed @ normed.T

    # Cluster
    dist = 1.0 - sim
    np.fill_diagonal(dist, 0)
    dist = np.clip(dist, 0, None)
    condensed = squareform(dist)
    Z = linkage(condensed, method="average")
    labels = fcluster(Z, t=CLUSTER_THRESHOLD, criterion="distance")

    # Group by cluster and name them by representative node
    cluster_groups = {}
    for i, label in enumerate(labels):
        cluster_groups.setdefault(int(label), []).append(i)

    sorted_clusters = sorted(cluster_groups.values(), key=len, reverse=True)

    cluster_names = {}
    cluster_color_map = {}
    for ci, members in enumerate(sorted_clusters):
        cluster_embs = embeddings[members]
        centroid = cluster_embs.mean(axis=0)
        centroid_norm = centroid / (np.linalg.norm(centroid) or 1)
        dists_to_centroid = cluster_embs @ centroid_norm
        rep_idx = members[np.argmax(dists_to_centroid)]
        rep_name = valid_ids[rep_idx]

        if len(members) > 1:
            name = rep_name
        else:
            name = rep_name

        color = CLUSTER_COLORS[ci % len(CLUSTER_COLORS)]
        for m in members:
            nid = valid_ids[m]
            cluster_names[nid] = name
            cluster_color_map[nid] = color

    # Compute semantic neighbors for each node
    neighbors_map = {}
    for i, nid in enumerate(valid_ids):
        sims = [(valid_ids[j], float(sim[i, j])) for j in range(len(valid_ids)) if j != i]
        sims.sort(key=lambda x: x[1], reverse=True)
        neighbors_map[nid] = [{"id": s[0], "score": round(s[1], 3)} for s in sims[:TOP_NEIGHBORS]]

    # Build output nodes
    out_nodes = []
    for nid in ids:
        cluster = cluster_names.get(nid, "Uncategorized")
        color = cluster_color_map.get(nid, "#aaaaaa")
        node = {
            "id": nid,
            "summary": summaries.get(nid, ""),
            "cluster": cluster,
            "color": color,
            "neighbors": neighbors_map.get(nid, []),
        }
        if skeletons.get(nid):
            node["skeleton"] = skeletons[nid]
        if urls.get(nid):
            node["url"] = urls[nid]
        out_nodes.append(node)

    # Build links from curated edges (only those connecting known nodes)
    out_links = []
    for e in edges_raw:
        src = e.get("source")
        tgt = e.get("target")
        if src in id_set and tgt in id_set:
            out_links.append({
                "source": src,
                "target": tgt,
                "predicate": e.get("predicate", "related_to"),
            })

    # Unique cluster names for legend
    seen = {}
    for nid in ids:
        c = cluster_names.get(nid, "Uncategorized")
        if c not in seen:
            seen[c] = cluster_color_map.get(nid, "#aaaaaa")

    data = {
        "nodes": out_nodes,
        "links": out_links,
        "clusters": list(seen.keys()),
        "colors": seen,
    }

    with open(OUTPUT, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Built data.json: {len(out_nodes)} nodes, {len(out_links)} links, {len(seen)} clusters")


if __name__ == "__main__":
    main()
