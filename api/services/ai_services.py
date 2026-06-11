import os
from groq import Groq
from pydantic import BaseModel, Field
from django.conf import settings

# Initialize the Groq client
client = Groq(api_key=settings.GROQ_API_KEY)

# 1. Define the exact type conversion/structure you want
class InventoryItem(BaseModel):
    item_name: str
    category: str
    quantity: int
    confidence_score: float

def convert_text_to_structured_data(user_raw_text: str) -> str:
    """
    Takes unformatted user text and converts it strictly into 
    the InventoryItem JSON type framework.
    """
    
    # 2. Instruct the model and enforce JSON schema
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a data conversion assistant. You strictly output JSON "
                    f"that matches this schema: {InventoryItem.model_json_schema()}"
                )
            },
            {
                "role": "user",
                "content": f"Convert this text into structured data: {user_raw_text}"
            }
        ],
        model="llama-3.1-8b-instant",  # Fast, free, open-source model on Groq
        response_format={"type": "json_object"} # Forces JSON mode
    )
    
    # Returns a guaranteed raw JSON string matching your model types
    return chat_completion.choices[0].message.content