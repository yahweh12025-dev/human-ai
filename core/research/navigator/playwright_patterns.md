# Playwright Multi-Step Navigation Research
Date: 2026-04-19

## Core Patterns for Autonomous Navigation
1. **State-Machine Approach**: Define clear states (e.g., `SEARCHING`, `CLICKING`, `EXTRACTING`) to track progress.
2. **Action-Observation Loop**: 
   - Action: Execute click/type/navigate.
   - Observation: Wait for selector/URL change $\rightarrow$ Snapshot DOM $\rightarrow$ Analyze with LLM.
3. **Dynamic Selector Handling**: Use a mix of data-attributes, ARIA labels, and relative positioning to avoid brittle CSS selectors.
4. **Session Persistence**: Reuse browser contexts to maintain login state via cookies/localStorage.

## Implementation Strategy for Navigator Agent
- Implement a `NavigatorState` class to track current URL, target goal, and history.
- Create a `navigation_loop` that continues until the `goal_met` condition is true or a max-step limit is reached.

## 🏗️ Proposed Navigator Agent Architecture (State-Machine)

### Core Components
1.  **NavigatorState**: A dataclass holding:
    *   
    *    (The high-level objective, e.g., "Find the price of XAUUSD")
    *    (Stack of actions taken and observations)
    *   : The Playwright browser context.
    *    (Safety stop).
2.  **NavigatorEngine**: The main loop.
    *   
    *   
        *   **Phase 1: Plan**: Based on  and , use the LLM (via hybrid_llm_router) to decide the *next action* (e.g., "click button with text 'Login'", "type 'query' into search box").
        *   **Phase 2: Action**: Execute the decided action using Playwright.
        *   **Phase 3: Observe**: Wait for network idle, snapshot the new DOM, and summarize the change for the LLM.
        *   **Phase 4: Evaluate**: Use the LLM to determine if the  has been met based on the new observation and history. If yes, break loop and return success.
3.  **Action Library**: A set of primitives the LLM can choose from:
    *   
    *   
    *   
    *   
    *   
    *   
    *   

### Integration
- The  will be instantiated by the  when it receives a task like "Perform web research on topic X."
- It will use the  for all reasoning, planning, and evaluation steps, making it a true Omni-Model agent.


## ✅ Finalized Design: Navigator State-Machine & Action-Observation Loop

### State Definition (NavigatorState)
*   : The URL the browser is currently on.
*   : The natural language objective from the task (e.g., "Find the latest Bitcoin price").
*   : A list of dictionaries. Each entry logs an action taken and the resulting observation.
*   : The active Playwright browser context (for session persistence).
*   : A safety counter to prevent infinite loops.
*   : The maximum number of steps allowed before the agent fails the task.

### The Action-Observation Loop (The Core Algorithm)
The  runs this loop until  is  or .

1.  **OBSERVE (Start of Loop)**:
    *   If it's the first step, the observation is the initial page state.
    *   Otherwise, it's the result of the previous action (DOM change, network request, URL change).
    *   The observation is processed into a concise text summary for the LLM (e.g., "Page loaded. Search box is visible. No results yet.").

2.  **PLAN (LLM as the Brain)**:
    *   Construct a prompt for the LLM (using ):
        *   **System Prompt**: "You are an expert web navigation agent. Your goal is to achieve the user's objective by selecting the NEXT SINGLE ACTION from the provided action library. You must think step-by-step."
        *   **Context**: The current , the  of past actions and observations, and the list of available actions.
        *   **Instruction**: "Based on the goal and history, what is the single best action to take now? Respond with ONLY the action name and its required arguments in JSON format. Example: {\"action\": \"click_selector\", \"arguments\": {\"selector\": \"#login-button\"}}"
    *   Call the LLM. Parse its JSON response to get the  and .

3.  **ACT (Execute with Playwright)**:
    *   Use the  and  to call the corresponding function from the Action Library (e.g., ).
    *   Wait for the action to settle (e.g., wait for network idle, or a specific selector to appear/disappear).
    *   Increment .

4.  **EVALUATE (LLM as the Judge)**:
    *   Construct a second prompt for the LLM:
        *   **Context**: The original , the full updated  (including the just-completed action and its fresh observation), and the current .
        *   **Instruction**: "Based on the goal and the complete history of actions and observations, has the goal been successfully achieved? Answer with ONLY 'YES' or 'NO'."
    *   Call the LLM. If the response is 'YES', set  and break the loop. If 'NO', continue to the next iteration.

5.  **RETURN**:
    *   If the loop breaks due to , return a  status with the final  and any extracted data.
    *   If the loop breaks due to , return a  status indicating the agent could not achieve the goal in the allowed steps.

### Integration with the Swarm
*   This  will be instantiated by the  when it pulls a task from  tagged as a web navigation or research task.
*   The engine's output (success/failure, data, history) will be formatted into a result that the  () can write to .
*   All reasoning and evaluation steps are handled by the , making this a true Omni-Model agent capable of switching between Gemini, DeepSeek, Perplexity, and Claude based on the complexity of the planning or evaluation step.

--- 
**Design Complete**. This architecture is ready for implementation. The next step is to create the  class in  based on this specification.

