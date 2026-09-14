"""
Demo: Expert Persona Registration
"""
import sys
import os

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from coordination import SupervisorAgent, AgentCommunication
from personas import ExpertSelector

def run_demo():
    print("--- 1. Initialize System ---")
    comm = AgentCommunication()
    supervisor = SupervisorAgent("Supervisor", comm)
    print("System initialized.")

    print("\n--- 2. Create Expert Persona ---")
    # Simulating the result of the LLM selection process
    turing = ExpertSelector.create_persona(
        name="Alan Turing",
        domain="Computing Foundations",
        reason="Pioneer of CS, perfect for deep theoretical analysis.",
        style="Mathematical, rigorous, focused on first principles.",
        capabilities=["cryptanalysis", "algorithm_design"]
    )
    print(f"Created Persona: {turing.name}")

    print("\n--- 3. Register Expert Agent ---")
    supervisor.register_expert("agent_turing", turing)
    
    worker = supervisor.workers["agent_turing"]
    print(f"Registered Agent: agent_turing")
    print(f"Capabilities: {worker['capabilities']}")
    print("\n--- 4. Verify System Prompt Injection ---")
    print("Generated System Prompt:")
    print("-" * 40)
    # Generate prompt with empty context for demo
    generator = worker.get('prompt_generator')
    if generator:
        print(generator("Demo Context: Analyze this..."))
    else:
        print("No prompt generator found.")
    print("-" * 40)

    print("\n--- 5. Verify Selection Prompt Template ---")
    print(ExpertSelector.get_selection_prompt("Analyze Bitcoin security"))

if __name__ == "__main__":
    run_demo()
