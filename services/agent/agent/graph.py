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
    delivery_task_id: str | None
    pending_sms: dict[str, str] | None


async def agent_node(state: SessionState, config: RunnableConfig) -> dict[str, Any]:
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

    # Route a small set of read-only requests through the same validated
    # functions exposed by MCP. Identity is scoped to the selected demo account by the service.
    from agent import mcp_server
    from agent.daytona_tasks import get_task, start_delivery_report_task
    import os

    pending_sms = state.get("pending_sms")
    if pending_sms and re.fullmatch(r'\s*(?:remi[,\s]+)?confirm send[.!\s]*', last_user_lower):
        try:
            if role != "manager":
                raise PermissionError()
            account = await mcp_server._require_manager()
            if pending_sms.get("channel") == "twilio":
                formatted = f"{pending_sms['message']}\n\n— {account['name']}"
                if formatted != pending_sms.get("formatted") or os.getenv("TWILIO_FROM_NUMBER") != pending_sms.get("sender"):
                    return {"messages": [AIMessage(content="SMS settings changed. Please review a new draft.")], "pending_sms": None}
            else:
                from agent.notifications import format_sms_gateway_address, format_staff_sms_body
                target = os.getenv("RESEND_TEST_RECIPIENT_OVERRIDE", "").strip() or format_sms_gateway_address(pending_sms["phone_number"], pending_sms["carrier"])
                formatted = format_staff_sms_body(pending_sms["message"], manager_name=account["name"], restaurant_phone=os.getenv("RESTAURANT_CONTACT_PHONE", "(619) 555-0144"), floor_phone=os.getenv("FLOOR_CONTACT_PHONE", "(619) 555-0182"))
                if target != pending_sms["target"] or formatted != pending_sms["formatted"]:
                    return {"messages": [AIMessage(content="Alert settings changed. Please create and review a new draft.")], "pending_sms": None, "last_action": "sms_cancelled"}
            result = await mcp_server.send_staff_sms_alert(
                phone_number=pending_sms["phone_number"], carrier=pending_sms.get("carrier"), message=pending_sms["message"]
            )
            provider = result.get("provider")
            if provider == "twilio":
                reply = "Twilio accepted the text for delivery. Delivery is not yet confirmed."
            elif provider == "resend":
                reply = "Resend accepted the email for the carrier gateway. Phone delivery is not confirmed."
            elif provider == "smtp":
                reply = "The email was sent to the carrier gateway. Phone delivery is not confirmed."
            else:
                reply = "The alert was simulated by the mock service; no text was sent."
        except PermissionError:
            reply = "Only an active manager can send this alert."
        except Exception:
            reply = "I could not confirm whether the alert was accepted. Check the provider before trying again."
        return {"messages": [AIMessage(content=reply)], "pending_sms": None, "last_action": "sms_dispatch"}
    if pending_sms and re.fullmatch(r'\s*(?:remi[,\s]+)?(?:cancel|cancel alert|cancel message)[.!\s]*', last_user_lower):
        return {"messages": [AIMessage(content="I cancelled the alert draft.")], "pending_sms": None, "last_action": "sms_cancelled"}
    if pending_sms:
        return {"messages": [AIMessage(content="The alert is awaiting your review. Say 'confirm send' to send it, or 'cancel alert' to discard it before making changes.")], "last_action": "sms_pending"}

    # An explicit format preserves the exact recipient and message for review.
    sms_match = re.match(r"^\s*(?:text|sms|send (?:a )?(?:text|sms) to)\s+(\+?[\d() .-]{8,24})\s*:\s*(.+)$", last_user_msg, re.I | re.S)
    if sms_match:
        try:
            account = await mcp_server._require_manager()
            if not all(os.getenv(key) for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER")):
                return {"messages": [AIMessage(content="Direct SMS is not configured. Set Twilio credentials and a sender number.")]}
            number, message = sms_match.group(1).strip(), sms_match.group(2).strip()
            if message.lower() in {"delivery report", "the delivery report"}:
                from agent.daytona_tasks import get_task
                task = get_task(state.get("delivery_task_id") or "")
                if not task or task.get("status") != "completed" or not task.get("report"):
                    raise ValueError("No completed delivery report")
                message = str(task["report"])
            if not message or len(message) > 1500:
                raise ValueError("Message is empty or too long")
            formatted = f"{message}\n\n— {account['name']}"
            return {"messages": [AIMessage(content=f"Review text to {number}: {formatted}\nSay confirm send to send it, or cancel.")],
                    "pending_sms": {"phone_number": number, "message": message, "channel": "twilio", "sender": os.environ["TWILIO_FROM_NUMBER"], "formatted": formatted}, "last_action": "sms_draft"}
        except PermissionError:
            return {"messages": [AIMessage(content="Sending a message requires an active manager account.")]}
        except ValueError:
            return {"messages": [AIMessage(content="The report is not ready, or the message is longer than 1,500 characters.")]}

    task_id = state.get("delivery_task_id")
    delivery_mentioned = bool(re.search(r'\b(daytona|deliver(?:y|ies)|marketman)\b', last_user_lower))
    status_requested = bool(re.search(r'\b(status|progress|ready|finished|complete|update)\b', last_user_lower))
    if task_id and status_requested and (delivery_mentioned or re.search(r'\b(report|task|it)\b', last_user_lower)):
        try:
            if role != "manager":
                raise PermissionError()
            await mcp_server._require_manager()
            task = get_task(task_id)
            if not task:
                reply = "I cannot find that report; tasks are cleared when the agent service restarts."
            elif task.get("status") == "completed":
                reply = "The delivery report is complete. " + str(task.get("report", ""))[:700]
            elif task.get("status") == "failed":
                reply = "The delivery report failed. " + str(task.get("error") or "Check the agent service for details.")
            else:
                reply = "The delivery report is " + str(task.get("status", "running")) + ". " + str(task.get("progress", ""))
        except PermissionError:
            reply = "Checking this report requires an active manager profile."
        except Exception:
            reply = "I could not verify your demo account. Check the mock service."
        return {"messages": [AIMessage(content=reply)], "last_action": "delivery_task_status"}

    if (delivery_mentioned and re.search(r'\b(report|analysis|analy[sz]e|plan(?:ning)?)\b', last_user_lower)
            and re.search(r'\b(start|run|create|generate|prepare|make|build|analy[sz]e|draft)\b', last_user_lower)):
        try:
            if role != "manager":
                raise PermissionError()
            await mcp_server._require_manager()
            if not os.getenv("DAYTONA_API_KEY"):
                reply = "Daytona is not configured. Set DAYTONA_API_KEY on the agent service to run the delivery report."
            else:
                task_id = start_delivery_report_task(os.getenv("MOCK_POS_BASE_URL", "http://localhost:8001").rstrip("/"))
                reply = "I started the mock MarketMan delivery report in Daytona. Ask me for its status while it runs. No purchase order will be submitted."
                return {"messages": [AIMessage(content=reply)], "last_action": "delivery_task_started", "delivery_task_id": task_id}
        except PermissionError:
            reply = "Starting the delivery report requires an active manager profile."
        except Exception:
            reply = "I could not start the delivery report. Check the mock service and Daytona configuration."
        return {"messages": [AIMessage(content=reply)], "last_action": "delivery_task"}

    tool = None
    tool_args: dict[str, Any] = {}
    capability_query = bool(re.search(r'\b(mcp|capabilit(?:y|ies)|tools|integrations)\b', last_user_lower))
    if capability_query:
        try:
            account = await mcp_server.get_my_account_status()
            if account.get("account_status") != "active":
                reads = "This account cannot access restaurant data while disabled."
            else:
                reads = "This assistant can read the menu"
                if role == "manager" and account.get("access_tier") == "manager":
                    reads += ", staff working now, today's shifts, and inventory"
                reads += " through the mock services."
            reply = (f"Your selected demo account is {account['name']} ({account['role']}, "
                     f"{account['account_status']}). {reads} "
                     + ("Managers can prepare a staff alert for confirmation and request a Daytona delivery report. " if role == "manager" and account.get("access_tier") == "manager" and account.get("account_status") == "active" else "")
                     +
                     "This staff assistant cannot submit orders or change restaurant records.")
        except Exception:
            reply = "I could not check your demo account. Please check the mock service."
        return {"messages": [AIMessage(content=reply)], "last_action": "capabilities"}
    if "menu" in last_user_lower or "what do you have" in last_user_lower:
        tool = mcp_server.get_menu
    elif (re.search(r'\b(who|staff|employees|team|people|workers)\b', last_user_lower)
          and re.search(r'\b(work(?:ing)?|on (?:the )?(?:clock|shift|duty)|clocked in)\b', last_user_lower)):
        tool = mcp_server.get_staff_working_now
    elif "today" in last_user_lower and "shift" in last_user_lower:
        tool = mcp_server.get_today_shifts
    elif "inventory" in last_user_lower:
        tool = mcp_server.get_inventory
    llm = None
    ai_res = None
    if not tool:
        llm = _get_llm()
        if llm is not None:
            # Only registered read tools are offered; their server-side role checks
            # remain authoritative for every invocation.
            available_tools = {name: getattr(mcp_server, name) for name in (
                *mcp_server.ASSISTANT_READ_TOOLS,
                *(mcp_server.ASSISTANT_MANAGER_READ_TOOLS if role == "manager" else ()),
            )}
            registered = {entry.name: entry for entry in await mcp_server.mcp.list_tools()}
            specs = [{"type": "function", "function": {"name": name,
                      "description": registered[name].description or name,
                      "parameters": registered[name].inputSchema}}
                     for name in available_tools]
            if role == "manager":
                specs.append({"type": "function", "function": {
                    "name": "send_staff_sms_alert",
                    "description": "Prepare an alert for the manager to review and explicitly confirm. This tool call only creates a draft. Ask for a US phone number, carrier, and actual message if missing; never invent them.",
                    "parameters": {"type": "object", "properties": {
                        "phone_number": {"type": "string"}, "carrier": {"type": "string"},
                        "message": {"type": "string"},
                    }, "required": ["phone_number", "carrier", "message"], "additionalProperties": False}}})
            try:
                account = await mcp_server.get_my_account_status()
                account_context = f"Selected demo account: {account['name']}, role {account['role']}, status {account['account_status']}."
            except Exception:
                account_context = "Selected demo account status is currently unavailable."
            prompt = SystemMessage(content=(
                "You are Remi, an operational voice assistant for Juniper Kitchen. "
                "You coordinate staff-to-staff operations, assist front-of-house, answer operational questions, "
                "and help managers review scheduling and inventory.\n\n"
                f"OPERATIONAL IDENTITY & ENVIRONMENT:\n"
                f"- Desktop demo profile role: {role}.\n"
                f"- {account_context}\n"
                f"- Integration Mock Base URL: http://localhost:8001 (or $MOCK_POS_BASE_URL)\n\n"
                "INTEGRATION CAPABILITIES & HTTP KNOWLEDGE:\n"
                "1. Resend API & Staff Notifications (POST /notifications/sms, POST https://api.resend.com/emails):\n"
                "   - Sends text notifications to staff mobile numbers via carrier Email-to-SMS gateways (e.g. {number}@vtext.com for Verizon, txt.att.net for AT&T, tmomail.net for T-Mobile).\n"
                "   - Outgoing texts automatically include manager signature and floor callback details.\n"
                "   - Inbound SMS replies from staff are caught via webhook at POST /webhooks/inbound-sms.\n"
                "   - Managers can use send_staff_sms_alert to prepare a draft. The service reviews it with the manager and sends only after explicit confirmation. Ask for missing phone, carrier, and message; do not invent them or claim delivery.\n"
                "2. Daytona Isolated Sandbox Execution (POST /tasks/daytona, GET /tasks/daytona/{task_id}):\n"
                "   - Used strictly for isolated, long-running, or analytical compute jobs (e.g., MarketMan YTD delivery and inventory planning reports).\n"
                "   - ordinary voice turns and POS reads stay on the fast direct loop (<1ms cache / local HTTP) to protect voice latency.\n"
                "   - Only managers can start or inspect Daytona background report jobs.\n"
                "3. Restaurant Integrations & POS HTTP Calls:\n"
                "   - Oracle POS: GET /oracle-pos/menu (menu items & pricing), POST /oracle-pos/checks (submit confirmed order), GET /oracle-pos/checks/{check_id}.\n"
                "   - 7shifts: GET /7shifts/v2/who_is_working_now (active staff), GET /7shifts/v2/shifts/today (scheduled shifts), GET /7shifts/v2/users/{id}, PUT /7shifts/v2/shifts/{shift_id} (optimistic locking with expected_version).\n"
                "   - MarketMan: GET /marketman/v1/inventory/items (stock levels & 86'd status), GET /marketman/v1/inventory/check-availability/{key}, GET /marketman/v1/receiving/ytd, POST /marketman/v1/inventory/deplete.\n\n"
                "RULES & GUARDRAILS:\n"
                "- Always use the available read tools to fetch live restaurant facts; never guess or hallucinate menu, shift, or stock data.\n"
                "- Server profiles can only access general menu, pricing, and public restaurant info.\n"
                "- Sensitive staff rosters, shift schedules, inventory numbers, SMS alerting, and Daytona analytics require an active manager account.\n"
                "- Prepare operational drafts for staff review. Do not commit or execute changes automatically.\n"
                "- Require explicit manager approval before any schedule change.\n"
                "- Keep guest order conversations in their separate workflow; do not conflate guest instructions with staff requests.\n"
                "- Keep spoken replies concise, natural, direct, and under 2 sentences."
            ))
            try:
                ai_res = await llm.bind_tools(specs).ainvoke([prompt, *messages])
                calls = getattr(ai_res, "tool_calls", [])
                if calls:
                    call = calls[0]
                    if call.get("name") == "send_staff_sms_alert" and role == "manager":
                        from agent.notifications import format_sms_gateway_address, format_staff_sms_body
                        args = call.get("args")
                        if not isinstance(args, dict) or set(args) != {"phone_number", "carrier", "message"} or any(not isinstance(v, str) or not v.strip() for v in args.values()):
                            return {"messages": [AIMessage(content="Please provide the staff member's phone number, mobile carrier, and the alert message.")], "last_action": "sms_incomplete"}
                        number, carrier, message = (args[key].strip() for key in ("phone_number", "carrier", "message"))
                        try:
                            gateway = format_sms_gateway_address(number, carrier)
                            if len(message) > 1000 or re.search(r'\[[^\]]+\]|\b(?:insert|placeholder)\b', message, re.I):
                                raise ValueError("Invalid draft")
                            account = await mcp_server._require_manager()
                        except (ValueError, PermissionError):
                            return {"messages": [AIMessage(content="Please provide a valid US phone number, supported carrier, and complete alert message.")], "last_action": "sms_incomplete"}
                        target = os.getenv("RESEND_TEST_RECIPIENT_OVERRIDE", "").strip() or gateway
                        formatted = format_staff_sms_body(message, manager_name=account["name"], restaurant_phone=os.getenv("RESTAURANT_CONTACT_PHONE", "(619) 555-0144"), floor_phone=os.getenv("FLOOR_CONTACT_PHONE", "(619) 555-0182"))
                        reply = f"Please review the alert to {number} via {carrier} (destination {target}): {formatted} Say 'confirm send' to send, or 'cancel alert' to discard it."
                        return {"messages": [AIMessage(content=reply)], "pending_sms": {"phone_number": number, "carrier": carrier, "message": message, "target": target, "formatted": formatted}, "last_action": "sms_draft"}
                    if call.get("name") not in available_tools or not isinstance(call.get("args"), dict):
                        return {"messages": [AIMessage(content="I cannot perform that action with the available read tools.")], "last_action": "unsupported_tool"}
                    tool = available_tools[call["name"]]
                    tool_args = call["args"]
            except Exception:
                ai_res = None

    if tool:
        if tool in (mcp_server.get_staff_working_now, mcp_server.get_today_shifts, mcp_server.get_inventory) and role != "manager":
            return {"messages": [AIMessage(content="This information requires an active manager profile.")], "last_action": "read_tool"}
        try:
            result = await tool(**tool_args)
            if tool is mcp_server.get_menu:
                items = result.get("items", [])[:6]
                reply = "The menu includes " + ", ".join(
                    f"{item['name']} for {item['price']} dollars" for item in items
                ) + "."
            elif tool is mcp_server.get_staff_working_now:
                workers = result.get("workers", [])
                names = [w["name"] for w in workers if w.get("status") == "active"]
                reply = "Currently working: " + (", ".join(names) if names else "no one") + "."
            elif tool is mcp_server.get_today_shifts:
                reply = f"There are {len(result.get('shifts', []))} shifts scheduled today."
            elif tool is mcp_server.get_inventory:
                inventory = result.get("inventory", {})
                unavailable = [v.get("name", k) for k, v in inventory.items() if v.get("is_86d") or v.get("on_hand", 0) <= 0]
                reply = "Out of stock: " + (", ".join(unavailable) if unavailable else "none") + "."
            elif tool is mcp_server.get_my_account_status:
                reply = f"The selected demo account is {result['name']}, {result['role']}; its account status is {result['account_status']}."
            else:
                import json
                reply = "Here is the result: " + json.dumps(result, default=str)[:1500]
        except PermissionError:
            reply = "This profile cannot access that information. Sign in as a manager to use this tool."
        except Exception:
            reply = "I could not reach the restaurant service. Please try again."
        return {"messages": [AIMessage(content=reply)], "last_action": "read_tool"}

    if llm is not None:
        # Use live OpenRouter LLM with injected store context, integration context, and role boundaries
        sys_prompt = (
            f"You are Remi, an operational voice assistant for Juniper Kitchen.\n"
            f"Current signed-in staff role: {role}.\n"
            f"{store_context}\n\n"
            "SYSTEM ARCHITECTURE & INTEGRATION CONTEXT:\n"
            "- Resend & SMS Notifications: Staff alerts can be dispatched via Email-to-SMS gateway (Resend API or SMTP). Inbound replies are received at /webhooks/inbound-sms.\n"
            "- Daytona Sandbox: Used strictly for isolated execution of heavy analytical tasks like the MarketMan YTD delivery and receiving report. Live voice turns and POS calls stay on the direct sub-second service loop.\n"
            "- Restaurant HTTP Endpoints:\n"
            "  * Oracle POS: /oracle-pos/menu (menu & prices), /oracle-pos/checks (create/fire check after confirmation)\n"
            "  * 7shifts: /7shifts/v2/who_is_working_now (roster), /7shifts/v2/shifts/today (shifts), /7shifts/v2/shifts/{id} (update shift)\n"
            "  * MarketMan: /marketman/v1/inventory/items (stock), /marketman/v1/receiving/ytd (order history), /marketman/v1/inventory/deplete (deplete stock)\n\n"
            "GUIDELINES:\n"
            "- Keep responses concise, direct, and under 2 sentences suitable for voice speech.\n"
            "- If the role is 'server', do NOT disclose management or payroll data.\n"
            "- If an item is 86'd (out of stock), politely inform the caller.\n"
            "- Prepare operational drafts for staff review. Require explicit manager approval before any schedule change.\n"
            "- Keep guest order conversations in their separate workflow; do not mix guest ordering into staff operations.\n"
            "- You cannot submit orders or change restaurant data directly. Consequential changes require explicit confirmation and manager approval. Never claim an action was completed unless verified."
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
            if ai_res is None:
                ai_res = await llm.ainvoke(llm_messages)
            reply = ai_res.content
        except Exception:
            reply = "I could not reach the language model. Please try again."
    else:
        # Deterministic restaurant conversational heuristics fallback for local MVP
        if "menu" in last_user_lower or "what do you have" in last_user_lower:
            reply = (
                f"Here is what we have on the menu today: Classic Cheeseburger ($14.50), "
                f"Truffle Fries ($8.00), and Draft IPA ($7.50). "
                f"Please note that the Crispy Chicken Sandwich is currently 86'd (sold out)."
            )
        elif "staff" in last_user_lower:
            reply = "You can ask who is working now or ask about today's shifts."
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
                reply = "I have noted your confirmation, but I cannot send this order to the kitchen yet."
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
