"""LangGraph workflow definition for restaurant voice agent sessions.

Each conversation turn runs through this graph. The session state maintains
isolated turn history, order drafts, and confirmation status, while the shared
store context is injected dynamically into the turn execution.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


def _get_llm() -> ChatOpenAI | None:
    """Returns ChatOpenAI configured for OpenRouter if credentials are provided."""
    import os

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("LLM_MODEL", "deepseek/deepseek-v4.1-flash-1017")
    provider_only = os.getenv("OPENROUTER_PROVIDER_ONLY", "relace/fp4")

    extra_body: dict[str, Any] = {}
    if provider_only:
        extra_body["provider"] = {
            "only": [provider_only.strip()],
            "allow_fallbacks": False,
        }

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.2,
        max_tokens=250,
        extra_body=extra_body if extra_body else None,
    )


class SessionState(TypedDict):
    """Per-session isolated state tracked across conversational turns."""

    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    account_id: int
    role: str
    current_draft: list[dict[str, Any]]
    order_confirmed: bool
    last_action: str | None


def agent_node(state: SessionState, config: RunnableConfig) -> dict[str, Any]:
    """Processes user input within the session, guided by the injected store context."""
    configurable = config.get("configurable", {})
    store_context = configurable.get("store_context", "")
    role = state.get("role", "server")

    # Read latest user message from LangChain BaseMessage or dict
    messages = state.get("messages", [])
    last_user_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            last_user_msg = str(m.content)
            break
        elif isinstance(m, dict) and m.get("role") in {"user", "human"}:
            last_user_msg = str(m.get("content", ""))
            break

    last_user_lower = last_user_msg.lower()
    draft = list(state.get("current_draft", []))
    confirmed = state.get("order_confirmed", False)
    action_taken = None

    llm = _get_llm()
    if llm is not None:
        # Use live OpenRouter LLM with injected store context and role boundaries
        sys_prompt = (
            f"You are Remi, an operational voice assistant for Juniper Kitchen.\n"
            f"Current signed-in staff role: {role}.\n"
            f"{store_context}\n"
            f"Guidelines:\n"
            f"- Keep responses concise, direct, and under 2 sentences suitable for voice speech.\n"
            f"- If the role is 'server', do NOT disclose management or payroll data.\n"
            f"- If an item is 86'd (out of stock), politely inform the caller.\n"
            f"- Require confirmation before sending orders to the kitchen."
        )
        llm_messages = [SystemMessage(content=sys_prompt)]
        for m in messages:
            if isinstance(m, (HumanMessage, AIMessage)):
                llm_messages.append(m)
            elif isinstance(m, dict):
                role_key = m.get("role")
                if role_key == "user":
                    llm_messages.append(HumanMessage(content=m.get("content", "")))
                elif role_key == "assistant":
                    llm_messages.append(AIMessage(content=m.get("content", "")))

        try:
            ai_res = llm.invoke(llm_messages)
            reply = ai_res.content
        except Exception as e:
            reply = f"I'm sorry, I encountered an issue connecting to the model: {e}"
    else:
        # Deterministic restaurant conversational heuristics fallback for local MVP
        if "menu" in last_user_lower or "what do you have" in last_user_lower:
            reply = (
                f"Here is what we have on the menu today: Classic Cheeseburger ($14.50), "
                f"Truffle Fries ($8.00), and Draft IPA ($7.50). "
                f"Please note that the Crispy Chicken Sandwich is currently 86'd (sold out)."
            )
        elif "who is working" in last_user_lower or "staff" in last_user_lower:
            if role != "manager":
                reply = "I'm sorry, looking up the staff roster requires a manager role."
            else:
                reply = "Currently clocked in: Dave Miller (Head Chef) and Elena Rostova (Shift Lead)."
        elif "burger" in last_user_lower or "order" in last_user_lower:
            draft = [{"item_id": "101", "name": "Classic Cheeseburger", "quantity": 1}]
            reply = (
                "I've added 1 Classic Cheeseburger ($14.50) to your check. "
                "Would you like to confirm and send this order to the kitchen?"
            )
            action_taken = "draft_updated"
        elif "yes" in last_user_lower or "confirm" in last_user_lower:
            if draft:
                confirmed = True
                action_taken = "order_ready_to_fire"
                reply = "Thank you! Confirming your order now. Sending check to the kitchen."
            else:
                reply = "There are no items on your check yet. What would you like to order?"
        else:
            reply = (
                f"Welcome to Remi. {store_context.splitlines()[1] if store_context else ''} "
                f"How can I help you today?"
            )

    assistant_message = AIMessage(content=reply)

    return {
        "messages": [assistant_message],
        "current_draft": draft,
        "order_confirmed": confirmed,
        "last_action": action_taken,
    }


def build_agent_graph() -> Any:
    """Builds and compiles the stateful LangGraph workflow with in-memory checkpointer."""
    workflow = StateGraph(SessionState)

    workflow.add_node("agent", agent_node)
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Compiled workflow instance
session_graph = build_agent_graph()
