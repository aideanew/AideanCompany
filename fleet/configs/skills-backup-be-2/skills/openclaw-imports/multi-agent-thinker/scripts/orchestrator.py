#!/usr/bin/env python3
"""
Orchestrator for Multi-Agent Thinker
Handles autonomous task complexity detection and routing.
"""

import sys
import argparse
from typing import Optional
from personas import ExpertSelector, ExpertPersona
from strategies import CognitiveStrategyManager, CognitiveMode, PromptEnhancer

class PatternOrchestrator:
    def __init__(self, task_description: str):
        self.task = task_description
        
    def detect_complexity(self) -> bool:
        """
        Heuristic to distinguish Simple vs Complex tasks.
        
        Simple: Clear, linear, standard tools (e.g., "Write a file", "Fix typo").
        Complex: Ambiguous, multi-step, deep reasoning (e.g., "Design system", "Analyze trade-offs").
        """
        # In a real agent, this would be an LLM classifier. 
        # Here we use keywords and length as a proxy.
        complexity_keywords = [
            "design", "analyze", "evaluate", "compare", "plan", "architecture", 
            "strategy", "reason", "critique", "optimize", "refactor"
        ]
        
        is_long = len(self.task) > 100
        has_keywords = any(k in self.task.lower() for k in complexity_keywords)
        
        return is_long or has_keywords

    def execute(self):
        print(f"--- Incoming Task: \"{self.task[:50]}...\" ---")
        
        # 1. Complexity Assumption
        # The IDE has already determined this is a complex task suitable for this skill.
        # We proceed directly to execution without script-level heuristics.
        print(">> [DECISION] Task routed by IDE as COMPLEX/SEMANTIC MATCH.")
        print(">> ACTION: Activate Multi-Agent Thinker Skill.")
        
        # 2. Strategy Detection
        mode = CognitiveStrategyManager.detect_mode(self.task)
        print(f">> Strategy Detected: {mode.name}")
        
        # 3. Prompt Enhancement (CV Method)
        enhanced_task = PromptEnhancer.enhance(self.task)
        if len(enhanced_task) > len(self.task):
            print(f">> Prompt Enhanced: Repetition applied ({len(enhanced_task.split(chr(10)))} segments)")
            
        # 4. Expert Selection (Simulation)
        # We simulate selecting an expert based on the task
        expert_name = "Domain Expert"
        if "design" in self.task.lower():
            expert_name = "Steve Jobs"
        elif "analyze" in self.task.lower():
            expert_name = "Sherlock Holmes"
            
        persona = ExpertSelector.create_persona(
            name=expert_name,
            domain="Relevant Field",
            reason="Auto-selected based on task keywords.",
            style="Professional and deep.",
            default_mode=mode
        )
        
        # 5. Execution Setup
        system_prompt = persona.generate_system_prompt(self.task, mode=mode)
        
        print(f">> Agent Activated: {persona.name}")
        print(f">> System Prompt Generated ({len(system_prompt)} chars).")
        print(">> Ready for Inference.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Thinker Orchestrator")
    parser.add_argument("task", help="The user task")task")
    
    args = parser.parse_args()
    
    orchestrator = PatternOrchestrator(args.task)
    orchestrator.execute()
