import random

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI


def get_llm_model(handler: str) -> tuple[str, BaseChatModel]:
    
    # 50/50 chance of Gemini and Groq and OpenAI
    gamble = random.randint(0, 2)

    if gamble == 0:
        gemini_models_list = [
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.0-flash"
        ]

        random_idx = random.randint(0, len(gemini_models_list)-1)
        model_name = gemini_models_list[random_idx]
        
        return model_name, ChatGoogleGenerativeAI(model=model_name)
    
    elif gamble == 1:     
        groq_models_list = [
            "deepseek-r1-distill-llama-70b",
            "qwen-qwq-32b",
            "llama-3.3-70b-versatile",
            "llama3-70b-8192",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ]
        
        random_idx = random.randint(0, len(groq_models_list)-1)
        
        model_name = groq_models_list[random_idx]
           
        return model_name, ChatGroq(model=model_name)
    
    else:
        a4f_base_url = "https://api.a4f.co/v1"
        a4f_models_list = [
            "provider-1/mistral-large", # yes
            "provider-6/gpt-4.1", # yes
            "provider-5/gpt-4.1-mini", # yes
            "provider-6/o3-pro",
            "provider-6/o4-mini-high",
            "provider-3/deepseek-v3", # yes
            "provider-6/gemini-2.5-flash-thinking", # yes
            "provider-3/grok-4-0709", # yes
        ]

        random_idx = random.randint(0, len(a4f_models_list)-1)

        model_name = a4f_models_list[random_idx]

        return model_name.split("/")[1], ChatOpenAI(model=model_name, base_url=a4f_base_url)
