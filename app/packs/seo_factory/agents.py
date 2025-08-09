from app.agents.loop import build_loop
from app.tools.serp import serp_search
from app.services.llm import get_chat
from app.agents.tracked import TrackedLLM

class KeywordResearcher:
    @classmethod
    def build(cls, redis, tenant_id: str):
        base = get_chat("default", temperature=0.1)
        tracked = TrackedLLM(base, tenant_id, "gpt-4o-mini")
        tools = [serp_search]
        return build_loop(tracked, tools, should_retry=lambda s: False)
