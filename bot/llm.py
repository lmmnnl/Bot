from bot.config import GigaChatKey
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage

LLM = GigaChat(
    credentials=GigaChatKey,
    scope="GIGACHAT_API_PERS",
    model="GigaChat",
    verify_ssl_certs=False, 
    streaming=False,
)

messages = [
    SystemMessage(
        content="Ты - помощник в обучении студентов, они спрашивают у тебя подсказки к заданиям и решения. Ты должен объяснять и подсказывать."
    )
]

def get_response(user_message: str) -> str:
    messages.append(HumanMessage(content=user_message))
    
    res = LLM.invoke(messages)
    
    return res.content
