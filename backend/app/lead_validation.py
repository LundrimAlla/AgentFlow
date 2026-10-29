"""Accept customer type only from an explicit user field declaration."""

import re
from typing import Literal

from app.schemas.chat import Message

DECLARATION = re.compile(
    r"^\s*customer[ _]type\s*:\s*(B2B|B2C|unknown|unspecified)\s*[.!]?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def declared_customer_type(messages: list[Message]) -> Literal["B2B", "B2C"] | None:
    """Latest user declaration wins; conflicts clear the value, assistant text is ignored.

    Deliberately accept a narrow field syntax, not a guess from company names,
    quoted examples, negations or free-form mentions. Unrecognized prose abstains.
    """
    result: Literal["B2B", "B2C"] | None = None
    for message in messages:
        if message.role != "user":
            continue
        values = {match.upper() for match in DECLARATION.findall(message.content)}
        if values:
            result = "B2B" if values == {"B2B"} else "B2C" if values == {"B2C"} else None
    return result
