"""
Custom controls for Rouint's interactive UI.
"""
from __future__ import annotations

from typing import Union
import questionary
from questionary import Choice, Separator
from questionary.prompts.common import InquirerControl

class AlignedInquirerControl(InquirerControl):
    """
    Custom InquirerControl that preserves strict vertical alignment across
    enabled and disabled choices by omitting Questionary's default '- ' prefix.
    """
    def _get_choice_tokens(self):
        tokens = []

        def append(index: int, choice: Choice):
            selected = choice.value in self.selected_options
            is_pointed = index == self.pointed_at

            if is_pointed:
                if self.pointer is not None:
                    tokens.append(("class:pointer", f" {self.pointer} "))
                else:
                    tokens.append(("class:text", " " * 3))
                tokens.append(("[SetCursorPosition]", ""))
            else:
                pointer_length = len(self.pointer) if self.pointer is not None else 1
                tokens.append(("class:text", " " * (2 + pointer_length)))

            if isinstance(choice, Separator):
                tokens.append(("class:separator", f"{choice.title}"))
            elif choice.disabled:
                # Disabled choice: preserve alignment, do not prepend '- '
                if isinstance(choice.title, list):
                    tokens.extend(choice.title)
                else:
                    tokens.append(("class:disabled", str(choice.title)))
            elif isinstance(choice.title, list):
                # FormattedText choice — on hover, only highlight token[0] (the
                # command name). Remaining tokens keep their original styles so
                # the description and grey hint are unaffected.
                if is_pointed:
                    for i, (style, text) in enumerate(choice.title):
                        tokens.append(("class:highlighted" if i == 0 else style, text))
                else:
                    tokens.extend(choice.title)
            elif selected:
                tokens.append(("class:selected", str(choice.title)))
            elif is_pointed:
                tokens.append(("class:highlighted", str(choice.title)))
            else:
                tokens.append(("class:text", str(choice.title)))

            tokens.append(("", "\n"))

        for i, c in enumerate(self.filtered_choices):
            append(i, c)

        if tokens:
            tokens.pop()  # Remove trailing newline

        return tokens
