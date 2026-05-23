"""Split response text into handoff lines and display text."""

_MAX_DISCORD_MSG_LEN = 1900


def split_handoff_lines(text: str) -> tuple[list[str], str]:
    """Extract [handoff] lines from text, returning (handoff_lines, clean_text).

    Each handoff line is stripped and truncated to Discord's message limit.
    """
    handoff_lines: list[str] = []
    clean_lines: list[str] = []
    for line in text.split("\n"):
        if line.strip().startswith("[handoff]"):
            handoff_lines.append(line.strip()[:_MAX_DISCORD_MSG_LEN])
        else:
            clean_lines.append(line)
    return handoff_lines, "\n".join(clean_lines).strip()
