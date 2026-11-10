import pytest
import networkx as nx
from backend.app.models import Skill, SkillDependency, User, UserSkill
from backend.app.ml.skill_graph import (
    build_skill_graph,
    validate_dependency_addition,
    get_direct_prerequisites,
    get_transitive_prerequisites,
    get_direct_dependents,
    get_transitive_dependents,
    get_dependency_path,
    get_topological_order,
    calculate_bottleneck_score,
    diagnose_prerequisites
)


# ==============================================================================
# Graph Foundation & Integrity Tests
# ==============================================================================

def test_graph_construction_with_disconnected_nodes(test_environment):
    db = test_environment["db"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Add a third disconnected skill
    linear_algebra = Skill(
        id=3,
        name="Linear Algebra",
        description="Foundational vector mathematics",
        category="Mathematics"
    )
    db.add(linear_algebra)
    db.commit()

    G = build_skill_graph(db)

    # All three skills must exist as nodes
    assert G.number_of_nodes() >= 3
    assert regression.id in G
    assert statistics.id in G
    assert linear_algebra.id in G
    assert G.nodes[linear_algebra.id]["name"] == "Linear Algebra"

    # Disconnected skill has in_degree and out_degree of 0
    assert G.in_degree(linear_algebra.id) == 0
    assert G.out_degree(linear_algebra.id) == 0


def test_one_hop_and_transitive_prerequisites(test_environment):
    db = test_environment["db"]

    # Create 3-tier chain: Algebra (3) -> Statistics (2) -> Regression (1)
    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    # Statistics depends on Algebra: Algebra -> Statistics
    dep1 = SkillDependency(parent_skill_id=algebra.id, child_skill_id=2, dependency_strength=0.9)
    # Regression depends on Statistics: Statistics -> Regression
    dep2 = SkillDependency(parent_skill_id=2, child_skill_id=1, dependency_strength=0.8)
    db.add_all([dep1, dep2])
    db.commit()

    G = build_skill_graph(db)

    # 1-hop prerequisites of Regression (1)
    direct_prereqs = get_direct_prerequisites(G, 1)
    assert len(direct_prereqs) == 1
    assert direct_prereqs[0]["skill_id"] == 2
    assert direct_prereqs[0]["name"] == "Statistics"
    assert direct_prereqs[0]["distance"] == 1
    assert direct_prereqs[0]["is_direct"] is True

    # Transitive (multi-hop) prerequisites of Regression (1)
    transitive = get_transitive_prerequisites(G, 1)
    assert len(transitive) == 2
    transitive_map = {t["skill_id"]: t for t in transitive}

    # Immediate: Statistics (distance 1)
    assert transitive_map[2]["distance"] == 1
    assert transitive_map[2]["is_direct"] is True

    # Root foundation: Algebra (distance 2)
    assert transitive_map[3]["distance"] == 2
    assert transitive_map[3]["is_direct"] is False
    assert transitive_map[3]["path_names"] == ["Algebra", "Statistics", "Regression"]
    assert transitive_map[3]["dependency_strength"] == round(0.9 * 0.8, 3)


def test_descendant_and_transitive_dependents(test_environment):
    db = test_environment["db"]

    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    # Algebra -> Statistics -> Regression
    dep1 = SkillDependency(parent_skill_id=3, child_skill_id=2, dependency_strength=1.0)
    dep2 = SkillDependency(parent_skill_id=2, child_skill_id=1, dependency_strength=1.0)
    db.add_all([dep1, dep2])
    db.commit()

    G = build_skill_graph(db)

    # Direct dependents of Algebra
    direct_dep = get_direct_dependents(G, 3)
    assert len(direct_dep) == 1
    assert direct_dep[0]["skill_id"] == 2

    # Transitive dependents of Algebra (both Statistics and Regression)
    transitive_dep = get_transitive_dependents(G, 3)
    assert len(transitive_dep) == 2
    dep_ids = {d["skill_id"] for d in transitive_dep}
    assert dep_ids == {2, 1}


def test_dependency_path_retrieval(test_environment):
    db = test_environment["db"]

    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    db.add_all([
        SkillDependency(parent_skill_id=3, child_skill_id=2, dependency_strength=1.0),
        SkillDependency(parent_skill_id=2, child_skill_id=1, dependency_strength=1.0),
    ])
    db.commit()

    G = build_skill_graph(db)

    # Valid path: Algebra -> Regression
    path_info = get_dependency_path(G, source_skill_id=3, target_skill_id=1)
    assert path_info["has_path"] is True
    assert path_info["distance"] == 2
    assert path_info["path_ids"] == [3, 2, 1]
    assert path_info["path_names"] == ["Algebra", "Statistics", "Regression"]

    # Inverted path: Regression -> Algebra does not exist
    no_path = get_dependency_path(G, source_skill_id=1, target_skill_id=3)
    assert no_path["has_path"] is False
    assert no_path["distance"] is None


def test_topological_sort_dag(test_environment):
    db = test_environment["db"]

    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    # Algebra -> Statistics -> Regression
    db.add_all([
        SkillDependency(parent_skill_id=3, child_skill_id=2, dependency_strength=1.0),
        SkillDependency(parent_skill_id=2, child_skill_id=1, dependency_strength=1.0),
    ])
    db.commit()

    G = build_skill_graph(db)
    order = get_topological_order(G)

    # In topological sort, prerequisites must strictly precede dependents
    order_ids = [item["skill_id"] for item in order]
    assert order_ids.index(3) < order_ids.index(2)
    assert order_ids.index(2) < order_ids.index(1)


def test_cycle_detection_and_prevention():
    G = nx.DiGraph()
    G.add_node(1, name="Skill 1")
    G.add_node(2, name="Skill 2")
    G.add_node(3, name="Skill 3")

    # Path: 1 -> 2 -> 3
    G.add_edge(1, 2)
    G.add_edge(2, 3)

    # Attempting to add 3 -> 1 would create 1 -> 2 -> 3 -> 1 cycle
    with pytest.raises(ValueError) as exc:
        validate_dependency_addition(G, parent_skill_id=3, child_skill_id=1)
    assert "introduces a cyclic dependency loop" in str(exc.value)

    # Attempting to add self-loop 1 -> 1
    with pytest.raises(ValueError) as exc_self:
        validate_dependency_addition(G, parent_skill_id=1, child_skill_id=1)
    assert "cannot be its own prerequisite" in str(exc_self.value)

    # Attempting duplicate edge 1 -> 2
    with pytest.raises(ValueError) as exc_dup:
        validate_dependency_addition(G, parent_skill_id=1, child_skill_id=2)
    assert "already exists" in str(exc_dup.value)

    # Non-existent node 99 -> 1
    with pytest.raises(ValueError) as exc_miss:
        validate_dependency_addition(G, parent_skill_id=99, child_skill_id=1)
    assert "does not exist" in str(exc_miss.value)


# ==============================================================================
# Multi-Hop Learner Intelligence Tests
# ==============================================================================

def test_diagnose_skill_with_no_prerequisites(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    statistics = test_environment["statistics"]

    # Statistics has no dependencies
    diagnosis = diagnose_prerequisites(db, user.id, statistics.id)

    assert diagnosis["has_prerequisites"] is False
    assert diagnosis["primary_gap"] is None
    assert "has no prerequisite dependencies" in diagnosis["diagnosis_summary"]


def test_diagnose_all_prerequisites_mastered(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Statistics -> Regression
    db.add(SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.9))
    # User has high mastery in Statistics (0.85)
    db.add(UserSkill(user_id=user.id, skill_id=statistics.id, mastery=0.85, confidence=0.9))
    db.commit()

    diagnosis = diagnose_prerequisites(db, user.id, regression.id)

    assert diagnosis["has_prerequisites"] is True
    assert diagnosis["primary_gap"] is None
    assert "are healthy" in diagnosis["diagnosis_summary"]


def test_diagnose_single_weak_direct_prerequisite(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Statistics -> Regression
    db.add(SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.8))
    # User has weak mastery in Statistics (0.35)
    db.add(UserSkill(user_id=user.id, skill_id=statistics.id, mastery=0.35, confidence=0.4))
    db.commit()

    diagnosis = diagnose_prerequisites(db, user.id, regression.id)

    assert diagnosis["has_prerequisites"] is True
    assert diagnosis["primary_gap"] is not None
    gap = diagnosis["primary_gap"]
    assert gap["skill_id"] == statistics.id
    assert gap["name"] == "Statistics"
    assert gap["distance"] == 1
    assert gap["is_direct"] is True
    assert gap["mastery"] == 0.35
    assert "direct weak prerequisite" in gap["explanation"]


def test_diagnose_multi_hop_indirect_foundational_bottleneck(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Add Algebra: Algebra (3) -> Statistics (2) -> Regression (1)
    algebra = Skill(id=3, name="Algebra", category="Math")
    db.add(algebra)
    db.commit()

    db.add_all([
        SkillDependency(parent_skill_id=algebra.id, child_skill_id=statistics.id, dependency_strength=1.0),
        SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.8),
    ])

    # Statistics has moderate mastery (0.58), but root foundation Algebra has severe deficit (0.15)
    db.add_all([
        UserSkill(user_id=user.id, skill_id=statistics.id, mastery=0.58, confidence=0.7),
        UserSkill(user_id=user.id, skill_id=algebra.id, mastery=0.15, confidence=0.2),
    ])
    db.commit()

    diagnosis = diagnose_prerequisites(db, user.id, regression.id)

    assert diagnosis["has_prerequisites"] is True
    assert diagnosis["primary_gap"] is not None
    gap = diagnosis["primary_gap"]

    # The multi-hop intelligence must pinpoint Algebra as the root bottleneck!
    assert gap["skill_id"] == algebra.id
    assert gap["name"] == "Algebra"
    assert gap["distance"] == 2
    assert gap["is_direct"] is False
    assert gap["path_names"] == ["Algebra", "Statistics", "Regression"]
    assert "indirect foundational bottleneck" in gap["explanation"]


def test_diagnose_prerequisites_unenrolled_learner(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Statistics -> Regression
    db.add(SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.8))
    # User has no UserSkill record for Statistics
    db.commit()

    diagnosis = diagnose_prerequisites(db, user.id, regression.id)

    assert diagnosis["has_prerequisites"] is True
    assert diagnosis["primary_gap"] is not None
    gap = diagnosis["primary_gap"]
    assert gap["skill_id"] == statistics.id
    # Unenrolled prerequisite receives baseline 0.0 mastery without fabricating data
    assert gap["mastery"] == 0.0


def test_diagnose_user_level_data_isolation(test_environment):
    db = test_environment["db"]
    user = test_environment["user"]
    other_user = test_environment["other_user"]
    regression = test_environment["regression"]
    statistics = test_environment["statistics"]

    # Statistics -> Regression
    db.add(SkillDependency(parent_skill_id=statistics.id, child_skill_id=regression.id, dependency_strength=0.8))

    # User has mastered Statistics (0.90)
    # Other user has failed Statistics (0.10)
    db.add_all([
        UserSkill(user_id=user.id, skill_id=statistics.id, mastery=0.90, confidence=0.9),
        UserSkill(user_id=other_user.id, skill_id=statistics.id, mastery=0.10, confidence=0.2),
    ])
    db.commit()

    # User 1 diagnosis: healthy, no gap
    user1_diag = diagnose_prerequisites(db, user.id, regression.id)
    assert user1_diag["primary_gap"] is None

    # Other user diagnosis: gap detected on Statistics
    user2_diag = diagnose_prerequisites(db, other_user.id, regression.id)
    assert user2_diag["primary_gap"] is not None
    assert user2_diag["primary_gap"]["skill_id"] == statistics.id
    assert user2_diag["primary_gap"]["mastery"] == 0.10
