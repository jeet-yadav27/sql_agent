---
title: deep_research
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

