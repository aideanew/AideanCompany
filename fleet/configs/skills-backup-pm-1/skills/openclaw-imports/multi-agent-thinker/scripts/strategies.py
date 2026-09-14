from enum import Enum
import re
from typing import Dict, List, Optional

try:
    # 优先使用新技能的重复器
    from instruction_repeater.scripts.repeater import InstructionRepeater
except Exception:
    InstructionRepeater = None

class CognitiveMode(Enum):
    DEFAULT = "default"
    SOCRATIC = "socratic"         # 追问场景
    DIALECTICAL = "dialectical"   # 辩证场景
    PRE_MORTEM = "pre_mortem"     # 失败预想
    REVERSE_ENG = "reverse_eng"   # 反向提示
    MULTI_DIMENSIONAL = "multi_dim" # 多维解释

class PromptEnhancer:
    """
    Base Scenario: Prompt Enhancement
    Handles the mandatory repetition of user instructions to improve model performance.
    """
    
    @staticmethod
    def enhance(instruction: str) -> str:
        """
        Applies the repetition logic based on instruction length.
        
        Logic:
        - Length < 100 chars: Repeat 3 times (Total 4 segments).
        - Length 100-500 chars: Repeat 2 times (Total 3 segments).
        - Length > 500 chars: Repeat 1 time (Total 2 segments).
        
        Segments are separated by two newlines.
        """
        if InstructionRepeater:
            return InstructionRepeater.repeat(instruction)
        
        # 回退方案：保持原有逻辑，避免硬依赖
        length = len(instruction)
        if length < 100:
            count = 4
        elif length <= 500:
            count = 3
        else:
            count = 2
        return "\n\n".join([instruction] * count)

class CognitiveStrategyManager:
    """
    Extended Scenarios: Manages the 5 cognitive strategies.
    """
    
    _PROMPTS = {
        CognitiveMode.DEFAULT: "",
        
        CognitiveMode.SOCRATIC: """
**STRATEGY: SOCRATIC QUESTIONING (追问场景)**
1. Do NOT provide a solution immediately.
2. Ask ONE clarifying question at a time.
3. Iterate until you have 95% confidence in understanding the user's true needs and goals.
4. Only when fully clear, propose a solution.
""",

        CognitiveMode.DIALECTICAL: """
**STRATEGY: DIALECTICAL DISCUSSION (辩证场景)**
1. Act as a "Devil's Advocate" or "Opposer".
2. Challenge the user's assumptions, logic, and evidence.
3. Attack the idea from multiple angles to find loopholes.
4. Your goal is to make the final solution "bulletproof" by exposing all weaknesses.
5. Be direct and unsparing in your critique.
""",

        CognitiveMode.PRE_MORTEM: """
**STRATEGY: PRE-MORTEM ANALYSIS (失败预想)**
1. Assume the plan has ALREADY FAILED.
2. Analyze deeply:
   - What decision was wrong?
   - What was the most fatal error?
   - What core risk was ignored?
   - If we could start over, what is the first thing to fix?
3. Provide a "Failure Review" based on real-world similar failure cases.
""",

        CognitiveMode.REVERSE_ENG: """
**STRATEGY: REVERSE ENGINEERING (反向提示)**
1. Analyze mature, successful products in this domain (e.g., Amazon, Taobao for shopping).
2. Deduce the necessary features, requirements, and design choices from these finished products.
3. Output the inferred specification based on these industry standards.
""",

        CognitiveMode.MULTI_DIMENSIONAL: """
**STRATEGY: MULTI-DIMENSIONAL EXPLANATION (多维解释)**
Please provide your answer in TWO distinct parts:

1. **Beginner Version:**
   - Use simple language and analogies (like explaining to a layman).
   - Focus on intuition and core concepts.
   
2. **Expert Version:**
   - Use precise technical terminology.
   - Ensure absolute factual accuracy and depth.
   - Focus on nuance and implementation details.
"""
    }
    
    @classmethod
    def get_strategy_prompt(cls, mode: CognitiveMode) -> str:
        return cls._PROMPTS.get(mode, "")

    @staticmethod
    def detect_mode(instruction: str) -> CognitiveMode:
        """
        Simple keyword-based detection to infer the intended mode.
        In a real system, this might be another LLM call.
        """
        instruction_lower = instruction.lower()
        
        if any(x in instruction_lower for x in ["追问", "clarify", "unclear", "ask me"]):
            return CognitiveMode.SOCRATIC
        if any(x in instruction_lower for x in ["辩证", "devil's advocate", "critique", "challenge", "attack"]):
            return CognitiveMode.DIALECTICAL
        if any(x in instruction_lower for x in ["失败", "fail", "risk", "pre-mortem", "worst case"]):
            return CognitiveMode.PRE_MORTEM
        if any(x in instruction_lower for x in ["反向", "reverse", "deduce", "mature product"]):
            return CognitiveMode.REVERSE_ENG
        if any(x in instruction_lower for x in ["多维", "explain", "beginner", "expert version", "levels"]):
            return CognitiveMode.MULTI_DIMENSIONAL
            
        return CognitiveMode.DEFAULT
