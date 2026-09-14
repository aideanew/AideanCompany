"""
Instruction Repeater

提供纯函数式的指令重复能力，供其他技能复用。
"""

from typing import Final


class InstructionRepeater:
    """
    根据指令长度重复文本，以提升模型对关键信息的关注。
    """

    _SHORT_THRESHOLD: Final[int] = 100
    _MEDIUM_THRESHOLD: Final[int] = 500

    @staticmethod
    def repeat(instruction: str) -> str:
        """
        应用重复逻辑并返回拼接后的文本。

        规则：
        - 长度 < 100 字符：重复 3 次（总计 4 段）。
        - 长度 100–500 字符：重复 2 次（总计 3 段）。
        - 长度 > 500 字符：重复 1 次（总计 2 段）。
        - 段落之间使用两个换行符分隔。
        """
        length = len(instruction)

        if length < InstructionRepeater._SHORT_THRESHOLD:
            count = 4
        elif length <= InstructionRepeater._MEDIUM_THRESHOLD:
            count = 3
        else:
            count = 2

        return "\n\n".join([instruction] * count)


__all__ = ["InstructionRepeater"]
