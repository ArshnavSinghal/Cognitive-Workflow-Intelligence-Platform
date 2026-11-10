"""
CWIP Skill Dependency Graph & Multi-Hop Prerequisite Intelligence Module
Powered by NetworkX

Directed Graph Edge Convention:
    Prerequisite Skill -> Dependent Skill
    e.g., Statistics (id: 2) -> Regression (id: 1)
    
In this convention:
    - Predecessors of T: Direct prerequisites of T
    - Ancestors of T: All transitive (multi-hop) prerequisites of T
    - Successors of P: Direct dependent skills of P
    - Descendants of P: All downstream dependent skills of P
    - Path from P to T: Directed path representing the dependency chain P -> ... -> T
"""

import networkx as nx
from sqlalchemy.orm import Session
from ..models import Skill, SkillDependency, UserSkill


def build_skill_graph(db: Session) -> nx.DiGraph:
    """
    Constructs a NetworkX directed graph from skills and skill_dependencies in the database.
    
    Nodes: Skill IDs, with attributes {'name': str, 'category': str, 'description': str}
    Edges: (parent_skill_id, child_skill_id), with attributes {'strength': float, 'id': int}
    """
    G = nx.DiGraph()

    # Add all skills as nodes (including disconnected/isolated skills)
    skills = db.query(Skill).all()
    for s in skills:
        G.add_node(
            s.id,
            name=s.name,
            category=s.category or "",
            description=s.description or ""
        )

    # Add all prerequisite relationships as directed edges
    dependencies = db.query(SkillDependency).all()
    for d in dependencies:
        # Only add edge if both nodes exist in the graph
        if d.parent_skill_id in G and d.child_skill_id in G:
            G.add_edge(
                d.parent_skill_id,
                d.child_skill_id,
                strength=d.dependency_strength if d.dependency_strength is not None else 1.0,
                id=d.id
            )

    return G


def validate_dependency_addition(G: nx.DiGraph, parent_skill_id: int, child_skill_id: int) -> None:
    """
    Validates that adding a dependency (parent_skill_id -> child_skill_id) is permissible.
    
    Validation Rules:
    1. Parent and child must not be identical (no self-loops).
    2. Both parent and child must exist in the skill graph.
    3. The dependency edge must not already exist (no duplicate edges).
    4. Adding the edge must not create a directed cycle (DAG preservation).
    
    Raises ValueError with descriptive explanation if any rule is violated.
    """
    if parent_skill_id == child_skill_id:
        raise ValueError("A skill cannot be its own prerequisite (self-dependency rejected).")

    if parent_skill_id not in G:
        raise ValueError(f"Prerequisite skill (ID: {parent_skill_id}) does not exist.")

    if child_skill_id not in G:
        raise ValueError(f"Dependent skill (ID: {child_skill_id}) does not exist.")

    if G.has_edge(parent_skill_id, child_skill_id):
        raise ValueError("This prerequisite dependency already exists.")

    # Cycle detection:
    # If there is already a directed path from child_skill_id to parent_skill_id,
    # then adding (parent_skill_id -> child_skill_id) would complete a cycle!
    if nx.has_path(G, source=child_skill_id, target=parent_skill_id):
        cycle_path = nx.shortest_path(G, source=child_skill_id, target=parent_skill_id)
        path_names = [G.nodes[n].get("name", str(n)) for n in cycle_path]
        cycle_repr = " -> ".join(path_names)
        parent_name = G.nodes[parent_skill_id].get("name", str(parent_skill_id))
        raise ValueError(
            f"Adding this dependency introduces a cyclic dependency loop: "
            f"{cycle_repr} -> {parent_name}."
        )


def get_direct_prerequisites(G: nx.DiGraph, skill_id: int) -> list[dict]:
    """
    Returns immediate (1-hop) prerequisites of the specified skill.
    """
    if skill_id not in G:
        return []

    prereqs = []
    for p_id in G.predecessors(skill_id):
        edge_data = G.get_edge_data(p_id, skill_id, default={})
        prereqs.append({
            "skill_id": p_id,
            "name": G.nodes[p_id].get("name", ""),
            "category": G.nodes[p_id].get("category", ""),
            "dependency_strength": edge_data.get("strength", 1.0),
            "distance": 1,
            "is_direct": True
        })

    return sorted(prereqs, key=lambda x: x["name"])


def get_transitive_prerequisites(G: nx.DiGraph, skill_id: int) -> list[dict]:
    """
    Returns all transitive (multi-hop) prerequisites of the specified skill.
    Includes graph distance and the shortest dependency path.
    """
    if skill_id not in G:
        return []

    ancestors = nx.ancestors(G, skill_id)
    result = []

    for a_id in ancestors:
        shortest_path = nx.shortest_path(G, source=a_id, target=skill_id)
        distance = len(shortest_path) - 1
        is_direct = (distance == 1)

        # Get direct edge strength if direct, or product of strengths along path
        strength = 1.0
        for i in range(len(shortest_path) - 1):
            edge_data = G.get_edge_data(shortest_path[i], shortest_path[i + 1], default={})
            strength *= edge_data.get("strength", 1.0)

        path_names = [G.nodes[n].get("name", str(n)) for n in shortest_path]

        result.append({
            "skill_id": a_id,
            "name": G.nodes[a_id].get("name", ""),
            "category": G.nodes[a_id].get("category", ""),
            "distance": distance,
            "is_direct": is_direct,
            "dependency_strength": round(strength, 3),
            "path_ids": shortest_path,
            "path_names": path_names
        })

    # Sort by distance ascending, then by name
    return sorted(result, key=lambda x: (x["distance"], x["name"]))


def get_direct_dependents(G: nx.DiGraph, skill_id: int) -> list[dict]:
    """
    Returns immediate downstream skills that depend directly on the specified skill.
    """
    if skill_id not in G:
        return []

    dependents = []
    for d_id in G.successors(skill_id):
        edge_data = G.get_edge_data(skill_id, d_id, default={})
        dependents.append({
            "skill_id": d_id,
            "name": G.nodes[d_id].get("name", ""),
            "category": G.nodes[d_id].get("category", ""),
            "dependency_strength": edge_data.get("strength", 1.0),
            "distance": 1,
            "is_direct": True
        })

    return sorted(dependents, key=lambda x: x["name"])


def get_transitive_dependents(G: nx.DiGraph, skill_id: int) -> list[dict]:
    """
    Returns all downstream skills (multi-hop) that depend on the specified skill.
    """
    if skill_id not in G:
        return []

    descendants = nx.descendants(G, skill_id)
    result = []

    for d_id in descendants:
        shortest_path = nx.shortest_path(G, source=skill_id, target=d_id)
        distance = len(shortest_path) - 1
        path_names = [G.nodes[n].get("name", str(n)) for n in shortest_path]

        result.append({
            "skill_id": d_id,
            "name": G.nodes[d_id].get("name", ""),
            "category": G.nodes[d_id].get("category", ""),
            "distance": distance,
            "is_direct": (distance == 1),
            "path_ids": shortest_path,
            "path_names": path_names
        })

    return sorted(result, key=lambda x: (x["distance"], x["name"]))


def get_dependency_path(G: nx.DiGraph, source_skill_id: int, target_skill_id: int) -> dict:
    """
    Finds the shortest directed prerequisite path from source_skill_id to target_skill_id.
    """
    if source_skill_id not in G or target_skill_id not in G:
        return {
            "has_path": False,
            "distance": None,
            "path_ids": [],
            "path_names": [],
            "message": "One or both skill IDs not found in graph."
        }

    if not nx.has_path(G, source=source_skill_id, target=target_skill_id):
        return {
            "has_path": False,
            "distance": None,
            "path_ids": [],
            "path_names": [],
            "message": (
                f"No dependency path exists from {G.nodes[source_skill_id].get('name')} "
                f"to {G.nodes[target_skill_id].get('name')}."
            )
        }

    path = nx.shortest_path(G, source=source_skill_id, target=target_skill_id)
    path_names = [G.nodes[n].get("name", str(n)) for n in path]
    distance = len(path) - 1

    return {
        "has_path": True,
        "distance": distance,
        "path_ids": path,
        "path_names": path_names,
        "message": f"Path found with distance {distance}: {' -> '.join(path_names)}."
    }


def get_topological_order(G: nx.DiGraph) -> list[dict]:
    """
    Returns a topologically sorted sequence of skills, where foundational
    prerequisites appear before the skills that depend on them.
    """
    try:
        ordered_ids = list(nx.topological_sort(G))
        return [
            {
                "skill_id": sid,
                "name": G.nodes[sid].get("name", ""),
                "category": G.nodes[sid].get("category", "")
            }
            for sid in ordered_ids
        ]
    except nx.NetworkXUnfeasible:
        # Occurs if the graph contains a cycle
        return []


def calculate_bottleneck_score(
    mastery: float,
    confidence: float,
    dependency_strength: float,
    distance: int,
    num_downstream_dependents: int = 1
) -> float:
    """
    Deterministic scoring formula to evaluate which prerequisite represents the
    primary learning bottleneck for a struggling student.
    
    Formula:
        deficit = max(0.0, 1.0 - mastery)
        distance_factor = 1.0 + 0.2 * (distance - 1)  # Deep foundations prioritized
        confidence_factor = 1.0 - (0.4 * confidence) # Low confidence elevates urgency
        downstream_factor = 1.0 + 0.1 * min(num_downstream_dependents, 5) # Blocking impact
        
        score = deficit * dependency_strength * distance_factor * confidence_factor * downstream_factor
        
    Rationale:
        1. Mastery Deficit: Primary driver. The less mastery, the greater the bottleneck.
        2. Dependency Strength: Direct multiplier from pedagogical curricular strength.
        3. Root-Foundation Factor: A weak root (distance > 1) blocks all intermediate concepts.
           Repairing the foundational root prevents recurring plateaus.
        4. Confidence: When mastery is low and confidence is low, uncertainty is acute.
        5. Downstream Impact: A prerequisite that blocks multiple downstream topics is more vital.
    """
    deficit = max(0.0, 1.0 - mastery)
    distance_factor = 1.0 + 0.2 * max(0, distance - 1)
    confidence_factor = 1.0 - (0.4 * min(1.0, max(0.0, confidence)))
    downstream_factor = 1.0 + 0.1 * min(max(0, num_downstream_dependents), 5)

    raw_score = deficit * dependency_strength * distance_factor * confidence_factor * downstream_factor
    return round(raw_score, 4)


def diagnose_prerequisites(
    db: Session,
    user_id: int,
    target_skill_id: int,
    G: nx.DiGraph | None = None
) -> dict:
    """
    Performs full multi-hop prerequisite intelligence for a learner and target skill.
    
    1. Traverses all transitive prerequisites of target_skill_id via NetworkX ancestors.
    2. Retrieves the learner's actual mastery and confidence for each prerequisite.
    3. Evaluates potential gaps (mastery < 0.60 and risk >= 0.30).
    4. Ranks all deficient prerequisites using the deterministic bottleneck score.
    5. Identifies the primary bottleneck prerequisite and generates an explainable diagnosis.
    
    Strict User Isolation:
        Only UserSkill records matching user_id are queried. Unenrolled prerequisites
        are assigned baseline mastery 0.0 without fabricating historical data.
    """
    if G is None:
        G = build_skill_graph(db)

    target_node = G.nodes.get(target_skill_id)
    if not target_node:
        return {
            "target_skill_id": target_skill_id,
            "target_skill_name": "Unknown",
            "has_prerequisites": False,
            "prerequisites": [],
            "primary_gap": None,
            "diagnosis_summary": "Target skill does not exist in skill graph."
        }

    target_name = target_node.get("name", "")

    # Retrieve learner's mastery on target skill
    target_user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == user_id,
        UserSkill.skill_id == target_skill_id
    ).first()
    target_mastery = round(target_user_skill.mastery, 3) if target_user_skill else 0.0

    # Retrieve all transitive prerequisites
    transitive = get_transitive_prerequisites(G, target_skill_id)

    if not transitive:
        return {
            "target_skill_id": target_skill_id,
            "target_skill_name": target_name,
            "target_mastery": target_mastery,
            "has_prerequisites": False,
            "prerequisites": [],
            "primary_gap": None,
            "diagnosis_summary": f"{target_name} has no prerequisite dependencies. Learner can practice directly."
        }

    # Fetch UserSkill records for all prerequisites in a single query
    prereq_ids = [p["skill_id"] for p in transitive]
    user_skills = db.query(UserSkill).filter(
        UserSkill.user_id == user_id,
        UserSkill.skill_id.in_(prereq_ids)
    ).all()
    user_skill_map = {us.skill_id: us for us in user_skills}

    diagnosed_prereqs = []
    gap_prereqs = []

    for p in transitive:
        pid = p["skill_id"]
        p_name = p["name"]
        distance = p["distance"]
        strength = p["dependency_strength"]
        is_direct = p["is_direct"]
        path_names = p["path_names"]

        us = user_skill_map.get(pid)
        is_enrolled = us is not None
        mastery = round(us.mastery, 3) if us else 0.0
        confidence = round(us.confidence, 3) if us else 0.0

        # Risk calculation consistent with CWIP standard
        risk = round((1.0 - mastery) * strength, 3)
        potential_gap = (mastery < 0.60 and risk >= 0.30)

        # Count downstream dependents for bottleneck impact
        num_downstream = len(nx.descendants(G, pid)) if pid in G else 0

        bottleneck_score = calculate_bottleneck_score(
            mastery=mastery,
            confidence=confidence,
            dependency_strength=strength,
            distance=distance,
            num_downstream_dependents=num_downstream
        )

        item = {
            "skill_id": pid,
            "name": p_name,
            "category": p["category"],
            "distance": distance,
            "is_direct": is_direct,
            "dependency_strength": strength,
            "is_enrolled": is_enrolled,
            "mastery": mastery,
            "confidence": confidence,
            "risk": risk,
            "potential_gap": potential_gap,
            "bottleneck_score": bottleneck_score,
            "path_names": path_names
        }
        diagnosed_prereqs.append(item)

        if potential_gap:
            gap_prereqs.append(item)

    # Determine primary bottleneck
    primary_gap = None
    if gap_prereqs:
        # Highest bottleneck score first; break ties by distance descending (foundational root first)
        gap_prereqs.sort(key=lambda x: (x["bottleneck_score"], x["distance"]), reverse=True)
        top = gap_prereqs[0]

        chain_str = " -> ".join(top["path_names"])
        if top["is_direct"]:
            explanation = (
                f"{top['name']} is a direct weak prerequisite for {target_name}. "
                f"Learner mastery is {round(top['mastery'] * 100, 1)}% (risk {top['risk']}), "
                f"which directly hinders advancement."
            )
        else:
            explanation = (
                f"{top['name']} is an indirect foundational bottleneck for {target_name} "
                f"(distance {top['distance']}, chain: {chain_str}). "
                f"Learner mastery is {round(top['mastery'] * 100, 1)}% (risk {top['risk']}), "
                f"which blocks upstream concepts in the curriculum."
            )

        primary_gap = {
            "skill_id": top["skill_id"],
            "name": top["name"],
            "distance": top["distance"],
            "is_direct": top["is_direct"],
            "mastery": top["mastery"],
            "risk": top["risk"],
            "bottleneck_score": top["bottleneck_score"],
            "path_names": top["path_names"],
            "explanation": explanation
        }

        diagnosis_summary = (
            f"Prerequisite gap detected: {primary_gap['explanation']} "
            f"Recommended next action: practice_prerequisite on {top['name']}."
        )
    else:
        diagnosis_summary = (
            f"All {len(transitive)} prerequisite dependencies for {target_name} are healthy "
            f"(mastery >= 60% or risk < 0.30). Learner is well-prepared for {target_name}."
        )

    return {
        "target_skill_id": target_skill_id,
        "target_skill_name": target_name,
        "target_mastery": target_mastery,
        "has_prerequisites": True,
        "prerequisites": diagnosed_prereqs,
        "primary_gap": primary_gap,
        "diagnosis_summary": diagnosis_summary
    }
