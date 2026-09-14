
import sys
import os

# Ensure we can import from local directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies import PromptEnhancer, CognitiveStrategyManager, CognitiveMode

def run_verification():
    print("=== VERIFICATION: COGNITIVE STRATEGIES TRIGGER & LOGIC ===\n")
    
    # 1. Verify Base Scenario: Prompt Enhancement
    print("--- 1. Base Scenario: Prompt Enhancement (Repetition Logic) ---")
    
    short_cmd = "What is justice?" # < 100 chars
    medium_cmd = "A" * 150 # 100-500 chars
    long_cmd = "B" * 600 # > 500 chars
    
    print(f"\n[Short Command (<100 chars)] Input len: {len(short_cmd)}")
    enhanced_short = PromptEnhancer.enhance(short_cmd)
    segments_short = enhanced_short.split("\n\n")
    print(f"Result: {len(segments_short)} segments (Expected 4)")
    print(f"Content Preview: {enhanced_short[:50]}...")
    
    print(f"\n[Medium Command (100-500 chars)] Input len: {len(medium_cmd)}")
    enhanced_med = PromptEnhancer.enhance(medium_cmd)
    segments_med = enhanced_med.split("\n\n")
    print(f"Result: {len(segments_med)} segments (Expected 3)")
    
    print(f"\n[Long Command (>500 chars)] Input len: {len(long_cmd)}")
    enhanced_long = PromptEnhancer.enhance(long_cmd)
    segments_long = enhanced_long.split("\n\n")
    print(f"Result: {len(segments_long)} segments (Expected 2)")
    
    # 2. Verify Extended Scenarios: Mode Detection
    print("\n--- 2. Extended Scenarios: Strategy Trigger Detection ---")
    
    scenarios = [
        ("I want to build a shopping app, but I'm vague on details. Can you ask me questions to clarify?", CognitiveMode.SOCRATIC),
        ("My plan is to launch next week. Play devil's advocate and tell me why it will fail.", CognitiveMode.DIALECTICAL),
        ("Assume the launch failed catastrophically. Do a pre-mortem analysis.", CognitiveMode.PRE_MORTEM),
        ("I want a video app. Reverse engineer TikTok to give me a spec.", CognitiveMode.REVERSE_ENG),
        ("Explain quantum physics. Give me a beginner version and an expert version.", CognitiveMode.MULTI_DIMENSIONAL),
        ("Just write a hello world program.", CognitiveMode.DEFAULT)
    ]
    
    for input_text, expected_mode in scenarios:
        detected_mode = CognitiveStrategyManager.detect_mode(input_text)
        status = "PASS" if detected_mode == expected_mode else "FAIL"
        print(f"\nInput: '{input_text}'")
        print(f"Detected: {detected_mode.value} | Expected: {expected_mode.value} -> [{status}]")
        
        if detected_mode != CognitiveMode.DEFAULT:
            prompt = CognitiveStrategyManager.get_strategy_prompt(detected_mode)
            print(f"Injected System Prompt Snippet: {prompt.strip().splitlines()[0]}...")

if __name__ == "__main__":
    run_verification()
