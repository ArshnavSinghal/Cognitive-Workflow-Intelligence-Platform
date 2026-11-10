"""
Scenario-based synthetic development data for CWIP.

These records validate the ML pipeline only.
They are not real learner outcomes.
"""

import random


def _determine_outcome(action, mastery, recent_score, consistency, error_rate):
    """Generate a simulated outcome label."""

    if action == "practice_prerequisite":
        return "positive" if consistency > 0.5 else "neutral"

    if action == "practice_current":
        if recent_score > 70 and error_rate < 0.1:
            return "positive"
        if recent_score < 50:
            return "negative"
        return "neutral"

    if action == "easy_practice":
        return "positive" if mastery < 0.5 else "neutral"

    if action == "hard_practice":
        return (
            "positive"
            if mastery > 0.65 and recent_score > 70
            else "negative"
        )

    if action == "review_concept":
        return "positive" if consistency < 0.6 else "neutral"

    if action == "take_assessment":
        if mastery > 0.75:
            return "positive"
        if mastery < 0.35:
            return "negative"
        return "neutral"

    return "neutral"


def _choose_action(mastery, confidence, activity_count,
                   recent_score, consistency, error_rate):
    """Apply a deterministic policy to representative learner states."""

    if mastery < 0.30:
        return "easy_practice"

    if error_rate > 0.20 and mastery < 0.70:
        return "review_concept"

    if mastery < 0.60 and consistency > 0.65:
        return "practice_prerequisite"

    if mastery > 0.70 and recent_score > 75 and consistency > 0.65:
        return "hard_practice"

    if activity_count >= 12 and confidence < 0.55:
        return "take_assessment"

    return "practice_current"


def generate_synthetic_dataset(n_samples=600, seed=42):
    """
    Generate synthetic learner states.

    Each action receives a representative scenario first. Remaining
    examples are generated from varied learner states and labelled
    by the same policy. Every row is marked as synthetic.
    """

    rng = random.Random(seed)
    dataset = []

    # Representative states make sure every action is exercised.
    scenarios = [
        # mastery, confidence, activity_count, avg_score,
        # recent_score, consistency, error_rate, difficulty
        (0.20, 0.45,  3, 35, 40, 0.60, 0.10, "easy"),
        (0.45, 0.75,  5, 60, 58, 0.80, 0.25, "medium"),
        (0.45, 0.70,  5, 60, 60, 0.80, 0.10, "medium"),
        (0.20, 0.60,  3, 40, 45, 0.70, 0.10, "easy"),
        (0.85, 0.85, 15, 85, 90, 0.90, 0.05, "hard"),
        (0.65, 0.40, 15, 68, 68, 0.60, 0.10, "medium"),
    ]

    # Desired action for each scenario is verified below.
    expected_actions = [
        "easy_practice",
        "review_concept",
        "practice_prerequisite",
        "easy_practice",
        "hard_practice",
        "take_assessment",
    ]

    # Generate the representative states first.
    for scenario, expected in zip(scenarios, expected_actions):
        mastery, confidence, count, avg, recent, consistency, error, difficulty = scenario

        action = _choose_action(
            mastery, confidence, count, recent, consistency, error
        )

        # Do not silently create mislabeled scenario examples.
        if action != expected:
            raise ValueError(
                f"Scenario expected {expected}, but policy returned {action}"
            )

        difficulty_weights = {"easy": 0.8, "medium": 1.0, "hard": 1.3}

        dataset.append({
            "features": {
                "average_score": avg,
                "recent_score": recent,
                "adjusted_score": round(avg * difficulty_weights[difficulty], 2),
                "avg_difficulty_weight": difficulty_weights[difficulty],
                "consistency": consistency,
                "error_rate": error,
                "mastery": mastery,
                "confidence": confidence,
                "activity_count": count,
                "trend": 1 if recent > avg + 5 else (-1 if recent < avg - 5 else 0)
            },
            "recommended_action": action,
            "actual_action": action,
            "mastery_change": 0.0,
            "outcome": "neutral",
            "is_synthetic": True
        })

    difficulties = {
        "easy": 0.8,
        "medium": 1.0,
        "hard": 1.3
    }

    # Generate the remaining varied learner states.
    for _ in range(max(0, n_samples - len(dataset))):
        mastery = round(rng.uniform(0.1, 0.95), 3)
        confidence = round(rng.uniform(0.2, 1.0), 3)
        activity_count = rng.randint(1, 20)

        avg_score = round(rng.uniform(30, 98), 2)
        recent_score = round(
            max(0, min(100, avg_score + rng.uniform(-15, 15))), 2
        )

        consistency = round(rng.uniform(0.3, 1.0), 3)
        error_rate = round(rng.uniform(0.0, 0.3), 3)

        difficulty = rng.choice(list(difficulties))
        weight = difficulties[difficulty]
        adjusted_score = round(avg_score * weight, 2)

        trend = (
            1 if recent_score > avg_score + 5
            else -1 if recent_score < avg_score - 5
            else 0
        )

        action = _choose_action(
            mastery, confidence, activity_count,
            recent_score, consistency, error_rate
        )

        outcome = _determine_outcome(
            action, mastery, recent_score, consistency, error_rate
        )

        if outcome == "positive":
            mastery_change = round(rng.uniform(0.06, 0.20), 3)
        elif outcome == "negative":
            mastery_change = round(rng.uniform(-0.15, -0.06), 3)
        else:
            mastery_change = round(rng.uniform(-0.04, 0.04), 3)

        dataset.append({
            "features": {
                "average_score": avg_score,
                "recent_score": recent_score,
                "adjusted_score": adjusted_score,
                "avg_difficulty_weight": weight,
                "consistency": consistency,
                "error_rate": error_rate,
                "mastery": mastery,
                "confidence": confidence,
                "activity_count": activity_count,
                "trend": trend
            },
            "recommended_action": action,
            "actual_action": action,
            "mastery_change": mastery_change,
            "outcome": outcome,
            "is_synthetic": True
        })

    return dataset
