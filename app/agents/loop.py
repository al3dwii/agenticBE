from typing import Any, Dict, List, Callable, Optional
import json, inspect
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from app.services.events import emit_event

def build_loop(
    llm,
    tools: List[Any],
    should_retry: Optional[Callable[[Exception, int], bool]] = None,
    system: Optional[str] = None,
):
    tool_map: Dict[str, Any] = {getattr(t, "__name__", t.__class__.__name__): t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    class Runner:
        async def arun(self, state: dict):
            tenant_id = state.get("tenant_id", "unknown")
            job_id = state.get("job_id", "ad-hoc")

            msgs = []
            if system:
                msgs.append(SystemMessage(content=system))
            user_payload = {k: v for k, v in state.items() if k not in ("tenant_id", "job_id")}
            msgs.append(HumanMessage(content=f"Input:\n{json.dumps(user_payload, ensure_ascii=False)}"))

            await emit_event(tenant_id, job_id, "plan", "started", {"input": user_payload})

            attempt = 0
            last_tool_result = None

            while True:
                try:
                    ai = await llm_with_tools.ainvoke(msgs)
                except Exception as exc:
                    attempt += 1
                    if should_retry and should_retry(exc, attempt):
                        continue
                    raise

                # **CRITICAL**: append the AI message BEFORE any ToolMessage
                msgs.append(ai)

                tool_calls = getattr(ai, "tool_calls", None)
                if tool_calls is None and hasattr(ai, "additional_kwargs"):
                    tool_calls = ai.additional_kwargs.get("tool_calls")

                await emit_event(
                    tenant_id, job_id, "plan", "finished",
                    {"assistant": getattr(ai, "content", "") or "", "tool_calls": tool_calls}
                )

                if tool_calls:
                    await emit_event(tenant_id, job_id, "act", "started", {"tool_calls": tool_calls})
                    for tc in tool_calls:
                        name = tc.get("name") or tc.get("function", {}).get("name")
                        raw_args = tc.get("args") or tc.get("function", {}).get("arguments") or "{}"
                        if isinstance(raw_args, str):
                            try:
                                args = json.loads(raw_args)
                            except Exception:
                                args = {}
                        else:
                            args = raw_args or {}

                        fn = tool_map.get(name)
                        if not fn:
                            err = {"error": f"Unknown tool '{name}'"}
                            msgs.append(ToolMessage(content=json.dumps(err), tool_call_id=tc.get("id") or "", name=name or "tool"))
                            await emit_event(tenant_id, job_id, "act", "progress", {"tool": name, "error": err})
                            continue

                        try:
                            res = fn(**args)
                            if inspect.iscoroutine(res):
                                res = await res
                        except Exception as e:
                            res = {"error": str(e)}

                        last_tool_result = res

                        msgs.append(
                            ToolMessage(
                                content=json.dumps(res, ensure_ascii=False),
                                tool_call_id=tc.get("id") or "",
                                name=name,
                            )
                        )
                        await emit_event(tenant_id, job_id, "act", "progress", {"tool": name, "args": args, "result": res})

                    # loop to let the model react to tool outputs
                    continue

                
                final = last_tool_result if last_tool_result is not None else (getattr(ai, "content", "") or "")
                await emit_event(tenant_id, job_id, "act", "finished", {"result": final})
                return final

    return Runner()

# # app/agents/loop.py
# from typing import Any, Dict, List, Callable, Optional
# import json
# from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
# from app.services.events import emit_event

# def _to_messages(payload: Any, system: Optional[str] = None) -> List[BaseMessage]:
#     """Coerce arbitrary payloads into a list of LC messages."""
#     msgs: List[BaseMessage] = []
#     if system:
#         msgs.append(SystemMessage(content=system))

#     # Already messages?
#     if isinstance(payload, list) and all(hasattr(m, "type") for m in payload):
#         # assume list[BaseMessage]
#         msgs.extend(payload)  # type: ignore[arg-type]
#         return msgs

#     if isinstance(payload, str):
#         msgs.append(HumanMessage(content=payload))
#     elif isinstance(payload, (dict, list)):
#         msgs.append(HumanMessage(content=json.dumps(payload)))
#     else:
#         msgs.append(HumanMessage(content=str(payload)))
#     return msgs


# class SimpleLoop:
#     def __init__(
#         self,
#         planner_llm: Any,
#         actor_llm: Any,
#         tools: List[Any],
#         should_retry: Optional[Callable[[Exception, int], bool]] = None,
#         system: Optional[str] = None,
#     ):
#         self.planner = planner_llm
#         self.actor = actor_llm
#         self.tools = tools
#         self.should_retry = should_retry or (lambda exc, attempt: False)
#         self.system = system

#     async def arun(self, state: dict):
#         tenant_id = state.get("tenant_id", "unknown")
#         job_id = state.get("job_id", "ad-hoc")

#         # ---- PLAN ----
#         await emit_event(tenant_id, job_id, "plan", "started", {"input": state})
#         plan_msg = await self.planner.ainvoke(_to_messages(state, self.system))
#         plan_text = getattr(plan_msg, "content", str(plan_msg))
#         await emit_event(tenant_id, job_id, "plan", "finished", {"plan": plan_text})

#         # ---- ACT ----
#         await emit_event(tenant_id, job_id, "act", "started", {"plan": plan_text})
#         attempt = 0
#         while True:
#             try:
#                 act_input = {"plan": plan_text, **state}
#                 result_msg = await self.actor.ainvoke(_to_messages(act_input, self.system))
#                 result_text = getattr(result_msg, "content", str(result_msg))
#                 await emit_event(tenant_id, job_id, "act", "finished", {"result": result_text})
#                 return result_text
#             except Exception as exc:
#                 attempt += 1
#                 if not self.should_retry(exc, attempt):
#                     await emit_event(tenant_id, job_id, "act", "failed", {"error": str(exc), "attempt": attempt})
#                     raise
#                 await emit_event(tenant_id, job_id, "act", "retrying", {"error": str(exc), "attempt": attempt})


# def build_loop(
#     llm: Any,
#     tools: List[Any],
#     should_retry: Optional[Callable[[Exception, int], bool]] = None,
#     system: Optional[str] = None,
# ) -> SimpleLoop:
#     """
#     Build a SimpleLoop.
#     - `llm` can be a tracked wrapper; we'll try to bind tools if supported.
#     - `system` is an optional system prompt to prepend to messages.
#     - `should_retry(exc, attempt)` controls retries of the ACT phase.
#     """
#     # Try to bind tools on the actor side; if not supported, just pass through.
#     try:
#         actor = llm.bind_tools(tools)
#     except AttributeError:
#         actor = llm

#     return SimpleLoop(
#         planner_llm=llm,
#         actor_llm=actor,
#         tools=tools,
#         should_retry=should_retry,
#         system=system,
#     )

# from typing import Any, Dict, List, Callable
# from app.services.events import emit_event

# class SimpleLoop:
#     def __init__(self, planner_llm, actor_llm, tools: List[Any], should_retry: Callable[[Dict], bool]):
#         self.planner = planner_llm
#         self.actor = actor_llm
#         self.tools = tools
#         self.should_retry = should_retry

#     async def arun(self, state: dict):
#         tenant_id = state.get("tenant_id", "unknown")
#         job_id = state.get("job_id", "ad-hoc")
#         # PLAN
#         await emit_event(tenant_id, job_id, "plan", "started", {"input": state})
#         plan = await self.planner.ainvoke(state)
#         await emit_event(tenant_id, job_id, "plan", "finished", {"plan": getattr(plan, "content", str(plan))})
#         # ACT
#         await emit_event(tenant_id, job_id, "act", "started", {"plan": getattr(plan, "content", str(plan))})
#         # The actor has tools bound (via tracked wrapper)
#         result = await self.actor.ainvoke({"plan": getattr(plan, "content", str(plan)), **state})
#         await emit_event(tenant_id, job_id, "act", "finished", {"result": getattr(result, "content", str(result))})
#         return getattr(result, "content", result)

# def build_loop(llm, tools: List[Any], should_retry: Callable[[Dict], bool]):
#     # Keep interface same but return our SimpleLoop with tools bound on actor side
#     actor = llm.bind_tools(tools)
#     return SimpleLoop(planner_llm=llm, actor_llm=actor, tools=tools, should_retry=should_retry)
