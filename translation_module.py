import os
import anthropic

# Initialize the Anthropics client
key = os.getenv('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=key)

system_message = "You are now Translate-GPT, the world's greatest translator. Translate the following text to English if it's in Japanese, or Japanese if it's in English. You will be paid a fee for every section you translate, so do your best. Just give the translation, do not say 'here is the translation' or anything similar."

def translate_text(text_chunk):
    """Translates a text chunk using the Anthropics API."""
    response = client.messages.create(
        max_tokens=4096,
        model="claude-3-5-sonnet-20240620",
        system=system_message,
        messages=[
            {"role": "user", "content": text_chunk}
        ],
    )
    return response.content[0].text

def translate_string(input_text):
    """Splits the input text into chunks, translates each chunk, and returns the combined translation."""
    chunk_size = 45  # Define the chunk size
    chunks = [input_text[i:i+chunk_size] for i in range(0, len(input_text), chunk_size)]
    
    translated_text = ""
    past_history = []  # Initialize past_history to empty list

    for text_chunk in chunks:
        print("Sent text chunk.")
        # Get the API response
        translated_chunk = translate_text(text_chunk)
        past_history.append({"role": "user", "content": text_chunk})
        past_history.append({"role": "assistant", "content": translated_chunk})
        translated_text += translated_chunk + "\n"

    return translated_text.strip()
