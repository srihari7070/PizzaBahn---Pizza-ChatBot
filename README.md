# PizzaBahn Chatbot

This project is a simple pizza ordering chatbot built with a Python Flask backend and a JavaScript/HTML/CSS frontend. It uses the Google Gemini API to power its conversational capabilities, allowing users to place an order in a natural language format.

## Features
- Interactive chat interface for ordering pizzas, extras, and drinks.
- Menu management with support for dietary filters (e.g., Vegetarian, Vegan).
- Conversational flow to guide the user through the ordering process, including:
    - Asking for dietary needs.
    - Taking pizza, topping, extra, and drink selections.
    - Collecting customer information like name, phone, and address.
    - Providing a summary of the order for confirmation.
- Frontend design with a modern chat-like appearance, including a typing indicator and dynamic message display.
- Options menu in the frontend to view the menu, cancel, or restart an order.
- Speech-to-text functionality for user input, if supported by the browser.

## Prerequisites
- Python 3.x
- `pip` (Python package installer)

## Installation
1.  **Clone the Repository**
    ```bash
    git clone [your-repository-url]
    cd [your-repository-name]
    ```

2.  **Install Python Dependencies**
    The project relies on Flask for the web server and the Google Generative AI library for the chatbot logic. Install these packages using the provided `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Up the Google Gemini API Key**
    The chatbot uses the Google Gemini API. You will need to obtain an API key from the [Google AI Studio](https://aistudio.google.com/) and add it to the `main2.py` file.
    - Open `main2.py`.
    - Locate the line `api_key = "ADD_YOUR_APU_KEY_HERE"`.
    - Replace `"ADD_YOUR_APU_KEY_HERE"` with your actual API key.

## Running the Bot
To start the chatbot, run the `main2.py` script. This will launch the Flask development server.
```bash
python main2.py
