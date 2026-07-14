import gradio as gr
import pandas as pd
from dotenv import load_dotenv
import os
from research_manager import ResearchManager
import db_manager
from styles import CSS, JS, EXAMPLES, HEADER_HTML

load_dotenv(override=True)

# Ensure the database is initialized
db_manager.init_db()

async def run(query: str):
    """Run the analysis pipeline and yield logs step-by-step."""
    async for status_update in ResearchManager().run(query):
        yield status_update

def handle_upload(file):
    """Import Excel worksheets into SQLite and return updated schema & QA list."""
    if file is None:
        return "No file uploaded.", "", get_qa_dataframe()
    try:
        # Import Excel worksheets as SQLite tables
        tables = db_manager.import_excel_to_db(file.name)
        status = f"✅ Success! Imported {len(tables)} worksheet(s) into database: {', '.join(tables)}"
        
        # Get new schema
        schema = db_manager.get_database_schema()
        
        # Get QA dataframe
        qa_df = get_qa_dataframe()
        
        return status, schema, qa_df
    except Exception as e:
        return f"❌ Error loading Excel file: {str(e)}", "", get_qa_dataframe()

def get_qa_dataframe():
    """Retrieve cached Q&A pairs from database and return as a Pandas DataFrame."""
    pairs = db_manager.get_all_qa_pairs()
    if not pairs:
        return pd.DataFrame(columns=["Question", "SQL Query", "Answer Summary", "Created At"])
    return pd.DataFrame([
        {
            "Question": p["question"],
            "SQL Query": p["sql_query"],
            "Answer Summary": p["result_summary"][:150] + "..." if len(p["result_summary"]) > 150 else p["result_summary"],
            "Created At": p["created_at"]
        } for p in pairs
    ])

def refresh_ui_data():
    """Return current schema and QA pairs to initialize UI inputs."""
    schema = db_manager.get_database_schema()
    qa_df = get_qa_dataframe()
    return schema, qa_df

# UI Layout
with gr.Blocks(title="Excel/SQL Database Agent", css=CSS, js=JS) as ui:
    gr.HTML(HEADER_HTML)
    
    with gr.Row():
        # Left Panel (Sidebar-like layout for files, schemas, cache)
        with gr.Column(scale=1, min_width=350):
            gr.Markdown("### 📂 Upload Excel Database")
            file_uploader = gr.File(
                label="Select Excel File (.xlsx, .xls)",
                file_types=[".xlsx", ".xls"],
                type="filepath"
            )
            upload_status = gr.Markdown("No file uploaded yet.")
            
            gr.Markdown("### 🗄️ SQLite Database Schema")
            schema_display = gr.Markdown(db_manager.get_database_schema())
            
        # Right Panel (Query Box and Agent Execution Workspace)
        with gr.Column(scale=2):
            gr.Markdown("### 💬 Ask Questions about the Excel Data")
            with gr.Row(elem_classes="dr-query-row"):
                query_textbox = gr.Textbox(
                    placeholder="e.g. What are the total sales by product category?",
                    show_label=False,
                    container=False,
                    autofocus=True,
                    elem_id="dr-query",
                    scale=5,
                )
                run_button = gr.Button("Analyze", variant="primary", elem_id="dr-run", scale=1)
                
            gr.HTML('<div class="dr-examples-label">Try one</div>')
            gr.Examples(examples=EXAMPLES, inputs=query_textbox, elem_id="dr-examples")
            
            gr.Markdown("### 📜 Agent Investigation Logs & Report")
            report = gr.Markdown(elem_id="dr-report")

    # Bottom Area for Cached Q&As
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 💾 Common Q&A Cache Database (Router Memory)")
            qa_table = gr.Dataframe(
                value=get_qa_dataframe(),
                headers=["Question", "SQL Query", "Answer Summary", "Created At"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
                wrap=True
            )
            refresh_button = gr.Button("🔄 Refresh Database Views")

    # Connect components
    file_uploader.change(
        handle_upload,
        inputs=file_uploader,
        outputs=[upload_status, schema_display, qa_table]
    )
    
    # Run analysis logic (uses generator yielding step-by-step progress)
    run_button.click(run, inputs=query_textbox, outputs=report)
    query_textbox.submit(run, inputs=query_textbox, outputs=report)
    
    # When a run completes, let the user manually refresh cache if they want,
    # or trigger automatic refresh after completion.
    # Note: Gradio click handles multiple outputs, so we can refresh the table
    # on clicking refresh button.
    refresh_button.click(
        refresh_ui_data,
        outputs=[schema_display, qa_table]
    )
    
    # Initialize the UI views
    ui.load(
        refresh_ui_data,
        outputs=[schema_display, qa_table]
    )

if __name__ == "__main__":
    ui.launch()
