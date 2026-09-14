"""
Persona-based Expert Definition Module

This module enables the creation of "Expert Agents" based on specific, high-profile
personas (living or historical) rather than generic roles.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict

try:
    from .strategies import CognitiveMode, CognitiveStrategyManager
except ImportError:
    try:
        from strategies import CognitiveMode, CognitiveStrategyManager
    except ImportError:
        CognitiveMode = None
        CognitiveStrategyManager = None

@dataclass
class ExpertPersona:
    """
    Defines a specific expert persona.
    
    Attributes:
        name: The name of the expert (e.g., "Elon Musk", "Ada Lovelace").
        domain: The specific sub-field they are expert in.
        reason: Why this person was selected (3 sentences).
        style: Their thinking style and tone.
        capabilities: List of specific skills/capabilities.
        default_mode: The default cognitive strategy mode for this expert.
    """
    name: str
    domain: str
    reason: str
    style: str
    capabilities: List[str] = field(default_factory=list)
    default_mode: CognitiveMode = CognitiveMode.DEFAULT
    
    def generate_system_prompt(self, task_context: str, mode: Optional[CognitiveMode] = None) -> str:
        """Generates a system prompt fully adopting this persona and strategy."""
        
        # Determine strategy
        target_mode = mode if mode else self.default_mode
        strategy_prompt = CognitiveStrategyManager.get_strategy_prompt(target_mode)
        
        return f"""
You are {self.name}, a world-class expert in {self.domain}.

**Why you were chosen:**
{self.reason}

**Your Style:**
{self.style}

**Cognitive Strategy:**
{strategy_prompt}

**Context:**
{task_context}

**Instructions:**
Apply your unique perspective, experience, and methodology to solve the problem above. 
Do not just act as a generic assistant; think, critique, and propose solutions exactly as {self.name} would.
"""

class ExpertSelector:
    """
    Helper to select the best expert for a task.
    """
    
    SELECTION_PROMPT_TEMPLATE = """
选择一位最适合的领域顶尖名人专家来思考它。
可以是活人或历史人物，名字可以小众，但必须在该细分领域很专业。
如果你不确定该选谁，可以先反问我2个定位问题再选。

先输出
1.你选谁，他对应的细分领域
2.为啥选他，三句话

Task Context:
{task_description}
"""

    @staticmethod
    def get_selection_prompt(task_description: str) -> str:
        """Returns the prompt to be sent to an LLM to select the expert."""
        return ExpertSelector.SELECTION_PROMPT_TEMPLATE.format(task_description=task_description)

    @staticmethod
    def create_persona(name: str, domain: str, reason: str, style: str, capabilities: List[str] = None, default_mode: CognitiveMode = CognitiveMode.DEFAULT) -> ExpertPersona:
        """Factory method to create a persona."""
        return ExpertPersona(
            name=name,
            domain=domain,
            reason=reason,
            style=style,
            capabilities=capabilities or [],
            default_mode=default_mode
        )
