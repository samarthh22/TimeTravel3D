"""Conflict-aware feature tracks from geometrically verified pairwise matches."""


def build_tracks(edges):
    parent, members = {}, {}

    def root(node):
        if node not in parent:
            parent[node] = node
            members[node] = {node[0]: node[1]}
        if parent[node] != node:
            parent[node] = root(parent[node])
        return parent[node]

    conflicts = 0
    for a, b, pairs in sorted(edges, key=lambda edge: len(edge[2]), reverse=True):
        for ka, kb in pairs:
            ra, rb = root((a, int(ka))), root((b, int(kb)))
            if ra == rb:
                continue
            if set(members[ra]) & set(members[rb]):
                conflicts += 1
                continue
            if len(members[ra]) < len(members[rb]):
                ra, rb = rb, ra
            parent[rb] = ra
            members[ra].update(members.pop(rb))
    return [m for m in members.values() if len(m) >= 2], conflicts
