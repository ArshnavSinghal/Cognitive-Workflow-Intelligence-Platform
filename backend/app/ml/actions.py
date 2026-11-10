# Controlled action space for CWIP's recommendation engine.
# All recommended_action and actual_action values must use these codes.

ACTIONS = [
    "practice_current",       # Practice the current skill
    "practice_prerequisite",  # Practice a prerequisite skill
    "review_concept",         # Review weak concepts
    "easy_practice",          # Attempt easier problems
    "hard_practice",          # Attempt harder problems
    "take_assessment",        # Take a diagnostic assessment
]

ACTION_SET = set(ACTIONS)


def is_valid_action(action: str) -> bool:
    return action in ACTION_SET
