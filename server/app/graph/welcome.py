from langchain_core.messages import AIMessage

WELCOME_KIND = "welcome"

WELCOME_TEMPLATE = (
    "Hi {user_name}! I can help you connect data sources to ad destinations. "
)


def welcome_text(user_name: str) -> str:
    return WELCOME_TEMPLATE.format(user_name=user_name)


def welcome_message(user_name: str) -> AIMessage:
    return AIMessage(
        content=welcome_text(user_name),
        additional_kwargs={"kind": WELCOME_KIND},
    )
