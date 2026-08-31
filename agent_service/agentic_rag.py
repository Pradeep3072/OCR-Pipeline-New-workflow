import os
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import Tool
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import PromptTemplate
from backend.logger import get_logger
from backend.rag import retrieve_context

logger = get_logger(__name__)

def run_agentic_chat(task_id: str, question: str) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"answer": "Error: GROQ_API_KEY is not configured.", "contexts": []}
        
    # We use a powerful model for the reasoning agent
    llm = ChatGroq(temperature=0, groq_api_key=api_key, model_name="qwen/qwen3.6-27b")

    def search_document(query: str) -> str:
        """Search the uploaded document for context related to the query."""
        contexts = retrieve_context(task_id, query)
        if not contexts:
            return "No relevant information found in the document."
        return "\n\n---\n\n".join(contexts)

    ddg_search = DuckDuckGoSearchRun()

    def web_search(query: str) -> str:
        """Search the web when the answer is not found in the uploaded document."""
        return ddg_search.run(query)

    tools = [
        Tool(
            name="SearchDocument",
            func=search_document,
            description="Useful for searching information within the user's uploaded document. Always try this first before searching the web. Input should be a search query."
        ),
        Tool(
            name="WebSearch",
            func=web_search,
            description="Useful for searching the web when the answer is not found in the uploaded document. Input should be a search query."
        )
    ]

    # Use LangGraph's create_react_agent
    agent_executor = create_react_agent(llm, tools)

    try:
        # Pre-fetch contexts for evaluation metrics just in case
        contexts = retrieve_context(task_id, question)
        
        result = agent_executor.invoke({"messages": [("user", question)]})
        # The last message is the AI's final answer
        answer = result["messages"][-1].content
        
        return {
            "answer": answer,
            "contexts": contexts
        }
    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        return {"answer": f"Error running agent: {str(e)}", "contexts": []}
