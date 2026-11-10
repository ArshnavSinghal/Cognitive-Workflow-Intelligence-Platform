from sqlalchemy import text

from app.database import engine

with engine.begin() as connection:

    result = connection.execute(
        text("""
            UPDATE learning_outcomes
            SET is_test = TRUE
            WHERE id = :outcome_id
              AND is_test = FALSE
        """),
        {"outcome_id": 5}
    )

    print("Rows corrected:", result.rowcount)

    record = connection.execute(
        text("""
            SELECT id, is_test
            FROM learning_outcomes
            WHERE id = :outcome_id
        """),
        {"outcome_id": 5}
    ).fetchone()

    print("Verified record:", record)
