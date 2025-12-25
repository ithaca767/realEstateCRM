BEGIN;

CREATE TABLE IF NOT EXISTS transaction_deadlines (
    id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,

    deadline_type VARCHAR(50) NOT NULL,
    due_date DATE NOT NULL,

    completed_at DATE,
    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transaction_deadlines_transaction_id
    ON transaction_deadlines(transaction_id);

CREATE INDEX IF NOT EXISTS idx_transaction_deadlines_user_due
    ON transaction_deadlines(user_id, due_date);

COMMIT;
