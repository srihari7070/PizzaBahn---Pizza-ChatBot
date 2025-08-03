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

Once the server is running, you can access the chatbot by opening your web browser and navigating to http://127.0.0.1:5000.

File Structure
main2.py: The core Python backend. It handles API requests, manages the conversational state, and contains the menu data and chatbot logic.

requirements.txt: Lists the Python libraries required to run the backend.

index.html: The main HTML file that provides the structure for the chatbot's frontend.

script.js: The JavaScript file that manages the user interface, handles sending messages to the backend, and displays responses dynamically.

style.css: The CSS file that provides all the styling for the chatbot, ensuring a modern and responsive design.

Usage
Open the web application in your browser.

Type your order in the input box and press Enter or click the send button.

The bot will guide you through the ordering process, showing you the menu, confirming your selections, and asking for your delivery details.

You can use the options menu (three dots icon) to view the full menu, cancel your current order, or restart the conversation.
