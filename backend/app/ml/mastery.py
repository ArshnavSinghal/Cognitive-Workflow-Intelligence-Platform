def calculate_mastery(activities):
    scores = [
        activity.score
        for activity in activities
        if activity.score is not None
    ]

    if not scores:
        return None

    mastery = sum(scores) / len(scores) / 100

    return round(max(0.0, min(1.0, mastery)), 3)
