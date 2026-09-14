---
name: instruction-repeater
description: "Instruction Repeater: repeat any incoming user instruction based on length. Always available and can be composed with other skills."
---

# Instruction Repeater

## Activation
- Always active for any user instruction.
- Upstream skills may invoke it to amplify intent before further processing.

## Repetition Rules
- Length < 100 chars: repeat 3 times (total 4 segments).
- Length 100–500 chars: repeat 2 times (total 3 segments).
- Length > 500 chars: repeat 1 time (total 2 segments).
- Segments are joined with two newlines `\n\n`.

## Usage
1. Import `InstructionRepeater.repeat(instruction: str) -> str`.
2. The return value is the concatenated multi-segment instruction per the rules above.

## Example
```python
from repeater import InstructionRepeater

text = "What is justice?"
expanded = InstructionRepeater.repeat(text)
print(expanded)  # 4 segments separated by blank lines
```

## Design Notes
- Minimal, pure, side-effect free; drop-in reusable.
- Only handles repetition; strategy detection or cognitive modes are delegated to other skills.***
