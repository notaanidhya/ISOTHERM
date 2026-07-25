import sqlite3
import os

def check(db_path):
    print(f"\n=== Database: {db_path} ===")
    if not os.path.exists(db_path):
        print(f"File {db_path} does not exist.")
        return
    conn = sqlite3.connect(db_path)
    state_count = conn.execute("SELECT COUNT(*) FROM state_log").fetchone()[0]
    decision_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    action_count = conn.execute("SELECT COUNT(*) FROM action_queue").fetchone()[0]

    print(f"Total State Snapshots Recorded: {state_count}")
    print(f"Total Pending/Applied Actions:   {action_count}")
    print(f"Total LLM Decisions Logged:      {decision_count}")

    if decision_count > 0:
        row = conn.execute("SELECT sim_time_hours, llm_reasoning, action_taken FROM decisions ORDER BY id DESC LIMIT 1").fetchone()
        print("\n--- Latest Decision ---")
        print(f"Sim Hour:   {row[0]}")
        print(f"Reasoning:  {row[1]}")
        print(f"Action:     {row[2]}")

if __name__ == "__main__":
    check("sim_state.db")
    check("baseline_state.db")
