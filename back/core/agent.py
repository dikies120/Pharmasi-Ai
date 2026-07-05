from back.core.agents.chat_agent import ChatAgent
from back.core.agents.analytics_agent import AnalyticsAgent
from back.core.agents.validation_agent import ValidationAgent
from back.core.agents.dispensing_agent import DispensingAgent

class Agent(ChatAgent, AnalyticsAgent, ValidationAgent, DispensingAgent):
    pass
