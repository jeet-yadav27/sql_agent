from pydantic import BaseModel, Field
from agents import Agent
import os
from dotenv import load_dotenv

load_dotenv(override=True)
MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", "gpt-4o-mini")

# 1. Router Agent Schemas & Definition
class RouterDecision(BaseModel):
    use_cache: bool = Field(description="True if the question is identical or semantically identical to a cached question.")
    cached_question: str = Field(description="The exact matched cached question from the available list if use_cache is True, otherwise empty.")
    reason: str = Field(description="Reason for routing choice.")

ROUTER_INSTRUCTIONS = """
You are an intelligent database router. Your job is to determine whether a user's question can be answered 
by one of the questions in the cached Q&A database, or if we must generate a new SQL query.

Review the user's question and the list of available cached questions.
If there is a question in the cached list that is semantically equivalent, return use_cache = True and specify the cached question.
Otherwise, return use_cache = False.
"""

router_agent = Agent(
    name="Database Router Agent",
    instructions=ROUTER_INSTRUCTIONS,
    model=MODEL_NAME,
    output_type=RouterDecision
)

# 2. SQL Generator Agent Schemas & Definition
class GeneratedSQL(BaseModel):
    explanation: str = Field(description="Step-by-step logic of how the SQL query retrieves the correct data.")
    sql_query: str = Field(description="The complete, single executable SQLite query without markdown formatting or code blocks.")

GENERATOR_INSTRUCTIONS = """
You are an expert SQLite developer. Given a database schema containing table and column details, and a user's natural language question, 
generate a single executable SQLite query to answer the question.

Rules:
1. Only reference tables and columns that exist in the schema.
2. Return ONLY valid SQLite syntax. Do not wrap queries in markdown code blocks like ```sql ... ```.
3. Keep queries as simple and efficient as possible.
4. If you need to perform calculations, use standard SQLite aggregation functions (e.g. SUM, AVG, COUNT, MIN, MAX).
5. For text matches, prefer case-insensitive comparisons where appropriate (e.g., using LIKE).
"""

sql_generator_agent = Agent(
    name="SQL Generator Agent",
    instructions=GENERATOR_INSTRUCTIONS,
    model=MODEL_NAME,
    output_type=GeneratedSQL
)

# 3. SQL Evaluator Agent Schemas & Definition (Evaluator-Optimizer pattern)
class EvaluationFeedback(BaseModel):
    is_valid: bool = Field(description="True if the SQL query is syntactically valid and matches the given schema columns.")
    is_safe: bool = Field(description="True if the query is strictly read-only (no INSERT, UPDATE, DELETE, DROP, ALTER, CREATE).")
    feedback: str = Field(description="If valid and safe, write 'Passed'. Otherwise, describe exactly what is wrong or unsafe so the generator can fix it.")

EVALUATOR_INSTRUCTIONS = """
You are a database QA and security evaluator. Your task is to verify a generated SQLite query.

Review the query against the schema and user question, checking for:
1. Syntax and logic errors.
2. Column and table names (do they match the schema?).
3. Safety: Make sure the query is read-only. It must NOT contain any DDL or DML statements that alter the database (no DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, REPLACE, TRUNCATE).

Output your evaluation. If there are any issues, provide constructive feedback so the generator can optimize and correct it.
"""

sql_evaluator_agent = Agent(
    name="SQL Evaluator Agent",
    instructions=EVALUATOR_INSTRUCTIONS,
    model=MODEL_NAME,
    output_type=EvaluationFeedback
)

# 4. Answer Agent Schemas & Definition
class AnswerExplanation(BaseModel):
    markdown_answer: str = Field(description="A clear, professional answer explaining the SQL results, formatted in markdown.")

ANSWER_INSTRUCTIONS = """
You are a senior data analyst. You are provided with a user's question, the SQL query executed, and the query results.
Formulate a concise, clear, and professional response in markdown that explains the results and directly answers the user's question.
If the results are empty or there is an issue, explain that clearly to the user.
"""

answer_agent = Agent(
    name="Answer Agent",
    instructions=ANSWER_INSTRUCTIONS,
    model=MODEL_NAME,
    output_type=AnswerExplanation
)
