from __future__ import annotations

from collections import Counter, defaultdict

from .models import Challenge, Observation, ValidatorProfile


class _UnionFind:
    def __init__(self, values: list[str]):
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            parent = self.parent[value]
            self.parent[value] = root
            value = parent
        return root

    def union(self, left: str, right: str) -> None:
        a = self.find(left)
        b = self.find(right)
        if a != b:
            self.parent[b] = a


def build_clusters(
    validators: list[ValidatorProfile],
    pairwise: list[dict],
    *,
    threshold: float = 0.75,
    min_shared_failures: int = 2,
) -> list[dict]:
    ids = [item.id for item in validators]
    uf = _UnionFind(ids)
    for pair in pairwise:
        jaccard = pair.get("failure_jaccard")
        phi = pair.get("failure_phi")
        shared = int(pair.get("shared_failures") or 0)
        if shared < min_shared_failures:
            continue
        score = max(float(jaccard or 0.0), float(phi or 0.0))
        if score >= threshold:
            uf.union(pair["left"], pair["right"])

    groups: dict[str, list[str]] = defaultdict(list)
    for identifier in ids:
        groups[uf.find(identifier)].append(identifier)

    ordered = sorted(groups.values(), key=lambda members: (-len(members), members))
    return [
        {"id": f"C{index + 1}", "validators": sorted(members), "size": len(members)}
        for index, members in enumerate(ordered)
    ]


def annotate_cluster_failures(
    clusters: list[dict], challenges: list[Challenge], observations: list[Observation]
) -> list[dict]:
    challenge_map = {item.id: item for item in challenges}
    observations_by_validator: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        observations_by_validator[observation.validator_id].append(observation)

    enriched = []
    for cluster in clusters:
        families: Counter[str] = Counter()
        for validator_id in cluster["validators"]:
            for observation in observations_by_validator.get(validator_id, []):
                challenge = challenge_map.get(observation.challenge_id)
                if challenge is None or challenge.expected is None:
                    continue
                if observation.outcome != challenge.expected:
                    families[challenge.family] += 1
        item = dict(cluster)
        item["dominant_failure_families"] = [
            {"family": family, "events": count} for family, count in families.most_common(5)
        ]
        enriched.append(item)
    return enriched


def diversity_metrics(validators: list[ValidatorProfile], clusters: list[dict]) -> dict:
    if not validators:
        return {
            "nominal_validators": 0,
            "effective_failure_domains": 0.0,
            "normalized_diversity": 0.0,
            "largest_cluster_share": 0.0,
        }
    weights = {validator.id: validator.stake for validator in validators}
    total = sum(weights.values())
    cluster_weights = [sum(weights[item] for item in cluster["validators"]) for cluster in clusters]
    shares = [weight / total for weight in cluster_weights if total]
    effective = 1.0 / sum(share * share for share in shares) if shares else 0.0
    return {
        "nominal_validators": len(validators),
        "effective_failure_domains": effective,
        "normalized_diversity": effective / len(validators),
        "largest_cluster_share": max(shares, default=0.0),
    }
