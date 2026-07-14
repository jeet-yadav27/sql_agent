import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "app_data.db")

def init_db():
    """Initialize the SQLite database and create the common Q&A table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qa_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE,
            sql_query TEXT,
            result_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def import_excel_to_db(excel_file_path: str) -> list[str]:
    """
    Read all sheets from the Excel file and write them as tables to the SQLite database.
    Returns the list of table names created.
    """
    init_db()
    excel_file = pd.ExcelFile(excel_file_path)
    table_names = []
    
    conn = sqlite3.connect(DB_PATH)
    
    for sheet_name in excel_file.sheet_names:
        # Standardize table name (alphanumeric and underscores only)
        table_name = "".join([c if c.isalnum() else "_" for c in sheet_name]).strip("_").lower()
        if not table_name:
            table_name = "sheet_data"
            
        df = excel_file.parse(sheet_name)
        # Write to SQLite
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        table_names.append(table_name)
        
    excel_file.close()
    conn.close()
    return table_names

def get_database_schema() -> str:
    """Retrieve details about tables and their schemas in the database (excluding qa_pairs)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall() if row[0] not in ("qa_pairs", "sqlite_sequence")]
    
    schema_info = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        col_desc = [f"{col[1]} ({col[2]})" for col in columns]
        schema_info.append(f"Table: {table}\nColumns: {', '.join(col_desc)}")
        
    conn.close()
    
    if not schema_info:
        return "No Excel data tables found in database. Please upload an Excel file first."
    return "\n\n".join(schema_info)

def execute_query(sql_query: str) -> pd.DataFrame:
    """Execute a query and return a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    try:
        # Prevent any destructive or modifying operations in general queries
        upper_query = sql_query.upper().strip()
        destructive_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE", "TRUNCATE"]
        for keyword in destructive_keywords:
            # Simple keyword check (though LLM evaluation should verify safety more thoroughly)
            if f" {keyword} " in f" {upper_query} " or upper_query.startswith(keyword):
                raise ValueError(f"Modification commands like '{keyword}' are not allowed on this database.")
                
        df = pd.read_sql_query(sql_query, conn)
        return df
    finally:
        conn.close()

def search_qa_cache(question: str) -> dict | None:
    """Search for a question in the common Q&A database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Simple semantic/substring match for Q&A cache
    cursor.execute(
        "SELECT sql_query, result_summary FROM qa_pairs WHERE question LIKE ? OR ? LIKE '%' || question || '%'",
        (f"%{question}%", question)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def write_qa_cache(question: str, sql_query: str, result_summary: str):
    """Write a new Q&A pair to the database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO qa_pairs (question, sql_query, result_summary) VALUES (?, ?, ?)",
            (question, sql_query, result_summary)
        )
        conn.commit()
    finally:
        conn.close()

def get_all_qa_pairs() -> list[dict]:
    """Retrieve all cached Q&A pairs."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT question, sql_query, result_summary, created_at FROM qa_pairs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
