---
# title: deep_research
app_file: app.py
sdk: gradio
sdk_version: 6.14.0
---

## 1. The Work Flow Diagram
graph TD
    User([User Question]) --> Router{1. Router Agent}
    
    %% Cache Hit Path
    Router -- Cache Hit --> GetCache[Pull from Q&A Table]
    GetCache --> ReturnCache([Instantly Return Answer])
    
    %% Cache Miss Path
    Router -- Cache Miss --> SQLGen[2. SQL Generator Agent]
    SQLGen --> SQLEval{3. SQL Evaluator Agent}
    
    %% Evaluator-Optimizer Loop
    SQLEval -- Failed / Unsafe --> Feedback[Optimizer Feedback]
    Feedback -- Refinement Loop <br> max 3 iterations --> SQLGen
    
    %% Execution Path
    SQLEval -- Passed --> Execute[4. Execute Query on SQLite]
    Execute --> AnswerGen[5. Answer Agent Synthesizer]
    AnswerGen --> SaveCache[6. Save to Q&A Cache Table]
    SaveCache --> ReturnAnswer([Return Final Answer])



## 2. Detailed Step-by-Step Execution
Step 1: Routing (Semantic Cache Lookup)
Role: The Router Agent acts as a traffic controller.
Logic: When you ask a question, the Router compares it semantically to previously answered questions stored in the qa_pairs database table.
Result:
If it matches an existing entry (e.g., you ask "What are the total sales?" and the cache has "Show total sales"), it fetches the cached result and raw SQL instantly.
If it is a new question, it sends it to the SQL Generator.
Step 2: SQL Generation
Role: The SQL Generator Agent behaves like a senior developer.
Logic: It inspects the database tables and columns dynamically generated from your uploaded Excel sheet, and writes a SQLite query custom-tailored to answer your question.
Step 3: SQL Evaluation & Optimization (The Evaluator-Optimizer Pattern)
Role: The SQL Evaluator Agent acts as a security and code reviewer.
Logic: Before the query runs, the Evaluator validates it against the active schema. It ensures:
No syntax errors exist.
The table/column names match the schema.
Safety Check: The query is strictly read-only (no DROP, DELETE, INSERT, or UPDATE commands are allowed).
Optimization: If it finds issues, it returns detailed debugging feedback to the Generator. The Generator refines the query, and the Evaluator checks it again (allowing up to 3 attempts).
Step 4: SQL Execution
Logic: Once approved, the query is executed on the SQLite database, loading the results into a standard Python dataset (Pandas DataFrame).
Step 5: Answer Synthesis
Role: The Answer Agent acts as a data analyst.
Logic: It reads the raw data returned by the database and draft a clear, human-friendly markdown response explaining the findings.
Step 6: Archiving (Self-Learning Cache)
Logic: The system automatically saves the new question, SQL query, and answer explanation to the qa_pairs cache table. The agent dynamically learns from its execution history, making subsequent identical or similar queries instant.

