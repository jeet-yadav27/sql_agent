import asyncio
from agents import Runner, trace, gen_trace_id
from sql_agents import router_agent, sql_generator_agent, sql_evaluator_agent, answer_agent
import db_manager

class ResearchManager:

    async def run(self, query: str):
        """
        Run the Excel SQL agentic pipeline, yielding status updates and the final answer.
        """
        trace_id = gen_trace_id()
        with trace("Excel SQL Research Trace", trace_id=trace_id):
            yield f"🔍 Starting agentic analysis. Trace ID: {trace_id}\n\n"
            
            # Step 0: Check if tables exist in the database
            schema = db_manager.get_database_schema()
            if "No Excel data tables found" in schema:
                yield "⚠️ **Error:** No Excel data has been uploaded yet. Please upload an Excel file first using the sidebar."
                return
                
            # Step 1: Routing Check (Cache lookups)
            yield "📁 Checking the Q&A database for cached answers..."
            qa_pairs = db_manager.get_all_qa_pairs()
            
            # Formulate the list of questions for the Router Agent
            if qa_pairs:
                cached_questions_list = "\n".join([f"- {item['question']}" for item in qa_pairs])
                router_input = (
                    f"User Question: {query}\n\n"
                    f"Cached Questions in Database:\n{cached_questions_list}"
                )
                
                # Run the Router Agent
                router_result = await Runner.run(router_agent, router_input)
                decision = router_result.final_output
                
                if decision.use_cache and decision.cached_question:
                    # Find the answer for the matched question
                    cache_hit = db_manager.search_qa_cache(decision.cached_question)
                    if cache_hit:
                        yield f"✅ **Cache Hit!** Found an identical question: *\"{decision.cached_question}\"*\n\n"
                        yield f"### Cached SQL Query\n```sql\n{cache_hit['sql_query']}\n```\n\n"
                        yield f"### Answer\n{cache_hit['result_summary']}"
                        return
            
            yield "❌ No cache hit. Proceeding to generate a new SQL query...\n\n"
            
            # Step 2: Evaluator-Optimizer Loop
            sql_query = ""
            explanation = ""
            feedback_history = []
            max_iterations = 3
            iteration = 0
            success = False
            
            while iteration < max_iterations:
                iteration += 1
                yield f"🤖 **SQL Generator** (Iteration {iteration}/{max_iterations}): Planning and drafting SQL query..."
                
                # Prepare input with schema and feedback history if any
                generator_input = f"Database Schema:\n{schema}\n\nUser Question: {query}\n"
                if feedback_history:
                    generator_input += "\nPrevious attempts failed. See feedback:\n" + "\n".join(feedback_history)
                    
                generator_result = await Runner.run(sql_generator_agent, generator_input)
                generated_sql = generator_result.final_output
                
                sql_query = generated_sql.sql_query.strip()
                explanation = generated_sql.explanation
                
                yield f"💻 **Drafted SQL Query:**\n```sql\n{sql_query}\n```\n\n"
                yield "🛡️ **SQL Evaluator**: Reviewing the query for safety and correct columns..."
                
                # Run Evaluator
                evaluator_input = (
                    f"Database Schema:\n{schema}\n\n"
                    f"User Question: {query}\n\n"
                    f"Generated SQL: {sql_query}"
                )
                evaluator_result = await Runner.run(sql_evaluator_agent, evaluator_input)
                evaluation = evaluator_result.final_output
                
                if evaluation.is_valid and evaluation.is_safe:
                    yield "✅ **SQL Evaluator**: Query passes all validation checks!\n\n"
                    success = True
                    break
                else:
                    feedback_msg = f"Attempt {iteration} feedback: {evaluation.feedback}"
                    feedback_history.append(feedback_msg)
                    yield f"❌ **SQL Evaluator**: Validation failed!\n*Feedback: {evaluation.feedback}*\n\n"
                    
            if not success:
                yield "⚠️ **Warning:** The SQL Evaluator did not fully approve the query. We will attempt to run the latest version, but it may fail.\n\n"
                
            # Step 3: Run the query
            yield "⚙️ Running SQL query on database..."
            try:
                df = db_manager.execute_query(sql_query)
                yield f"✅ SQL executed successfully. Retrieved {len(df)} rows.\n\n"
                
                # Format the results as markdown table
                if len(df) > 0:
                    results_markdown = df.head(15).to_markdown(index=False)
                    if len(df) > 15:
                        results_markdown += f"\n\n*(Showing top 15 of {len(df)} rows)*"
                else:
                    results_markdown = "*Empty result table*"
                    
                yield f"### Raw SQL Results\n{results_markdown}\n\n"
                
            except Exception as e:
                yield f"❌ **Database Execution Error:** {str(e)}\n"
                return
                
            # Step 4: Answer Synthesis
            yield "✍️ **Answer Agent**: Synthesizing the final explanation..."
            answer_input = (
                f"Question: {query}\n\n"
                f"SQL Query: {sql_query}\n\n"
                f"SQL Results:\n{df.to_string(index=False)}"
            )
            answer_result = await Runner.run(answer_agent, answer_input)
            final_explanation = answer_result.final_output.markdown_answer
            
            # Step 5: Archive in Cache
            db_manager.write_qa_cache(query, sql_query, final_explanation)
            yield "💾 Question, SQL query, and answer archived to the Q&A database.\n\n"
            
            # Final output
            yield "### Final Answer\n" + final_explanation