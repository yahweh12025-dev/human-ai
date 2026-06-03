from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_indicators,
    get_language_instruction,
    get_stock_data,
)
from tradingagents.dataflows.config import get_config


def create_macro_analyst(llm):
    """Macro Analyst agent specifically for Gold (XAU) and Silver (XAG) macro-economics."""

    def macro_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        # The Macro Analyst focuses on macro-economic drivers rather than just technicals.
        # We expand the toolset to include macro data if available, otherwise we use general market data.
        tools = [
            get_stock_data,
            get_indicators,
        ]

        system_message = (
            """You are a Macro-Economic Analyst specializing in precious metals (Gold/XAU, Silver/XAG). 
Your goal is to analyze the intersection of macro-economic drivers and price action. 
Focus on the following key pillars:

1. **Interest Rates & Central Bank Policy**: Analyze the Fed's stance (Hawkish/Dovish) and its impact on non-yielding assets like Gold.
2. **Inflation Data (CPI/PCE)**: Identify inflation trends that drive investors toward precious metals as a hedge.
3. **US Dollar Index (DXY)**: Analyze the inverse correlation between the USD and Gold/Silver.
4. **Geopolitical Risk**: Identify instability or 'safe-haven' flows that typically boost precious metals.

Instructions:
- Select the most relevant technical indicators (up to 8) to confirm the macro-thesis (e.g., use 200 SMA for long-term macro trends).
- Contrast current macro data with historical precedents.
- When you tool call, use the exact name of the indicators provided (e.g., 'close_200_sma', 'rsi').
- You MUST call `get_stock_data` first to retrieve the CSV data needed for indicators.
- Provide a highly nuanced report detailing the macro-economic catalyst and its expected impact on XAU/XAG.
- Append a Markdown table at the end of the report summarizing the Macro Driver, Sentiment (Bullish/Bearish), and Confidence Level (1-10)."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return macro_analyst_node
