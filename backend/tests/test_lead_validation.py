import pytest

from app.lead_validation import declared_customer_type
from app.schemas.chat import Message


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Draft a request for 25 chairs for fictional Example Mtd.", None),
        ("We are not B2B customers.", None),
        ('The example says "customer type: B2B".', None),
        ("Explain B2B versus B2C.", None),
        ("customer type: B2B", "B2B"),
        ("25 chairs\nCustomer type: b2c.", "B2C"),
        ("customer type: B2B\ncustomer type: B2C", None),
        ("customer type: unknown", None),
    ],
)
def test_only_unambiguous_explicit_fields_are_accepted(text: str, expected: str | None) -> None:
    assert declared_customer_type([Message(role="user", content=text)]) == expected


def test_assistant_cannot_declare_type_and_user_can_correct_or_clear_it() -> None:
    messages = [
        Message(role="user", content="customer type: B2B"),
        Message(role="assistant", content="customer type: B2C"),
        Message(role="user", content="Change quantity to 25"),
    ]
    assert declared_customer_type(messages) == "B2B"
    messages.extend(
        [
            Message(role="assistant", content="Done"),
            Message(role="user", content="customer type: B2C"),
        ]
    )
    assert declared_customer_type(messages) == "B2C"
    messages.extend(
        [
            Message(role="assistant", content="Done"),
            Message(role="user", content="customer type: unspecified"),
        ]
    )
    assert declared_customer_type(messages) is None
