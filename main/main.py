import json
import sqlite3
import datetime
import re
import os
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import time
import uuid

app = Flask(__name__)
CORS(app)

api_key = "AIzaSyA3uWtiDlbpFANAEd-Ad6NggRwOkKclE98"
try:
    genai.configure(api_key=api_key)
    print("Gemini API configured successfully")
    
    # Test model initialization
    test_model = genai.GenerativeModel("gemini-2.5-flash")
    print("Gemini model 'gemini-2.5-flash' initialized successfully")
except Exception as e:
    print(f"Failed to initialize Gemini API/Model: {e}")

class OrderState:
    def __init__(self):
        self.step = "greeting"
        self.order_data = {
            "dietary_needs": None,
            "pizzas": [],
            "toppings": [],
            "pizza_preferences": [],
            "extras": [],
            "drinks": [],
            "customer_info": {
                "name": None,
                "phone": None,
                "address": None
            },
            "total_price": 0.0
        }
        self.has_asked_dietary = False
        self.has_shown_menu = False
        self.conversation_context = []
        
    def get_next_step(self):
        """Determine the next step based on current state - following flowchart exactly"""
        if self.step == "greeting":
            return "ask_dietary"
        
        elif self.step == "ask_dietary":
            if self.order_data["dietary_needs"]:
                return "show_menu"
            else:
                return "ask_dietary"
        
        elif self.step == "show_menu":
            return "ask_pizzas"
        
        elif self.step == "ask_pizzas":
            if self.order_data["pizzas"]:
                return "ask_toppings"
            else:
                return "ask_pizzas"
        
        elif self.step == "ask_toppings":
            return "ask_pizza_preferences"
        
        elif self.step == "ask_pizza_preferences":
            return "ask_sides_extras"

        elif self.step == "ask_sides_extras":
            return "ask_drinks"

        elif self.step == "ask_drinks":
            return "ask_address"
        
        elif self.step == "ask_address":
            if self.order_data['customer_info']['address']:
                return "ask_contact_info"
            else:
                return "ask_address"
        
        elif self.step == "ask_contact_info":
            if not self.order_data['customer_info']['name'] or not self.order_data['customer_info']['phone']:
                return "ask_contact_info"
            else:
                return "check_required_info"
        
        elif self.step == "check_required_info":
            if self.has_all_required_info():
                return "show_summary"
            else:
                return "ask_missing_info"
        
        elif self.step == "ask_missing_info":
            return "check_required_info"
        
        elif self.step == "show_summary":
            return "confirm_order"
        
        elif self.step == "confirm_order":
            return "place_order"
        
        elif self.step == "place_order":
            return "end_conversation"
        
        return "end_conversation"
    
    def has_all_required_info(self):
        """Check if all required information has been collected"""
        required_checks = [
            bool(self.order_data["dietary_needs"]),
            bool(self.order_data["pizzas"]),
            bool(self.order_data["customer_info"]["name"]),
            bool(self.order_data["customer_info"]["phone"]),
            bool(self.order_data["customer_info"]["address"])
        ]
        return all(required_checks)
    
    def get_missing_info(self):
        """Return list of missing required information"""
        missing = []
        if not self.order_data["dietary_needs"]:
            missing.append("dietary preferences")
        if not self.order_data["pizzas"]:
            missing.append("pizza selection")
        if not self.order_data["customer_info"]["name"]:
            missing.append("name")
        if not self.order_data["customer_info"]["phone"]:
            missing.append("phone number")
        if not self.order_data["customer_info"]["address"]:
            missing.append("delivery address")
        return missing
    
    def handle_order_rejection(self):
        """Handle when user says no to order confirmation - go back to menu"""
        self.step = "show_menu"
    
    def skip_toppings(self):
        """Handle when user doesn't want toppings"""
        self.step = "ask_pizza_preferences"
    
    def add_pizza_preference(self, preference):
        """Add pizza preferences like spicy level, cheese amount"""
        if preference not in self.order_data["pizza_preferences"]:
            self.order_data["pizza_preferences"].append(preference)

class MenuManager:
    def __init__(self):
        self.menu_data = {
            "pizzas": [
                {"id": "P1", "name": "Margherita", "type": "Vegetarian (Halal)", "description": "Tomato sauce, mozzarella, fresh basil | Contains dairy", "price": 8.50},
                {"id": "P2", "name": "Veggie Supreme", "type": "Vegetarian (Halal)", "description": "Bell peppers, mushrooms, red onions, olives, mozzarella | Contains dairy", "price": 9.50},
                {"id": "P3", "name": "Four Cheese", "type": "Vegetarian (Halal)", "description": "Mozzarella, cheddar, parmesan, gorgonzola | Contains dairy", "price": 10.00},
                {"id": "P4", "name": "Spicy Paneer", "type": "Vegetarian (Halal)", "description": "Paneer cubes, green chilies, red onion, tikka sauce, mozzarella | Contains dairy", "price": 10.50},
                {"id": "P5", "name": "Mediterranean Garden", "type": "Vegetarian (Halal)", "description": "Sun-dried tomatoes, feta, black olives, spinach, red onion", "price": 10.50},
                {"id": "P6", "name": "Vegan Delight (Halal)", "type": "Vegan (Halal)", "description": "Vegan cheese, cherry tomatoes, olives, spinach, red onion (Halal) | Contains dairy", "price": 9.00},
                {"id": "P7", "name": "Spicy Vegan Inferno (Halal)", "type": "Vegan (Halal)", "description": "Vegan cheese, chili flakes, jalapeños, hot tomato sauce (Halal) | Contains dairy", "price": 9.50},
                {"id": "P8", "name": "Vegan Pesto Paradise (Halal)", "type": "Vegan (Halal)", "description": "Vegan pesto, artichokes, arugula, cherry tomatoes (Halal) | Contains nuts", "price": 10.00},
                {"id": "P9", "name": "BBQ Jackfruit", "type": "Vegan (Halal)", "description": "BBQ jackfruit, vegan cheese, red onions, coriander (Halal) | Contains dairy", "price": 10.50},
                {"id": "P10", "name": "Vegan Mushroom Madness (Halal)", "type": "Vegan (Halal)", "description": "Mushrooms, garlic oil, spinach, vegan mozzarella (Halal) | Contains dairy", "price": 9.50},
                {"id": "P11", "name": "Pepperoni Feast", "type": "Non-Veg", "description": "Tomato sauce, mozzarella, spicy pepperoni | Contains dairy", "price": 10.50},
                {"id": "P12", "name": "BBQ Chicken", "type": "Non-Veg", "description": "BBQ sauce, grilled chicken, red onions, mozzarella | Contains dairy", "price": 11.00},
                {"id": "P13", "name": "Hawaiian", "type": "Non-Veg", "description": "Ham, pineapple, mozzarella, tomato sauce | Contains dairy", "price": 10.00},
                {"id": "P14", "name": "Chicken Tandoori", "type": "Non-Veg", "description": "Tandoori chicken, red onion, bell peppers, spicy yogurt base", "price": 11.50},
                {"id": "P15", "name": "Meat Lover's Special", "type": "Non-Veg", "description": "Pepperoni, sausage, bacon, ham, mozzarella | Contains dairy", "price": 12.00},
                {"id": "P16", "name": "Tuna & Onion", "type": "Non-Veg", "description": "Tuna, red onion, capers, mozzarella | Contains dairy", "price": 10.50},
            ],
            "extras": [
                {"id": "E1", "name": "Garlic Bread (4 pieces)", "type": "Vegetarian (Halal)", "price": 4.00, "description": "Contains gluten"},
                {"id": "E2", "name": "Garlic Bread w/ Cheese", "type": "Vegetarian (Halal)", "price": 4.50, "description": "Contains dairy | Contains gluten"},
                {"id": "E3", "name": "French Fries", "type": "Vegan (Halal)", "price": 3.50},
                {"id": "E4", "name": "Mozzarella Sticks (6 pcs)", "type": "Vegetarian (Halal)", "price": 5.00, "description": "Contains dairy"},
                {"id": "E5", "name": "BBQ Chicken Wings (6 pcs)", "type": "Non-Veg", "price": 6.50},
                {"id": "E6", "name": "Vegan Cauliflower Bites (Halal)", "type": "Vegan (Halal)", "price": 5.00},
            ],
            "drinks": [
                {"id": "D1", "name": "Coca-Cola", "size": "330ml", "price": 2.00},
                {"id": "D2", "name": "Fanta Orange", "size": "330ml", "price": 2.00},
                {"id": "D3", "name": "Sprite", "size": "330ml", "price": 2.00},
                {"id": "D4", "name": "Club Mate", "size": "500ml", "price": 2.50},
                {"id": "D5", "name": "Sparkling Water", "size": "500ml", "price": 1.50},
                {"id": "D6", "name": "Still Water", "size": "500ml", "price": 1.50},
                {"id": "B1", "name": "Berliner Kindl Pils", "type": "Pilsner", "size": "0.5L", "price": 3.50},
                {"id": "B2", "name": "BRLO Pale Ale", "type": "Craft Pale Ale", "size": "0.33L", "price": 4.00},
                {"id": "B3", "name": "Rothaus Tannenzäpfle", "type": "Lager / Pils", "size": "0.33L", "price": 3.80},
                {"id": "B4", "name": "Berliner Weisse (Rot/Grün)", "type": "Sour Wheat Beer", "size": "0.33L", "price": 4.20},
            ],
            "toppings": {
                "cheese": [
                    {"name": "Extra Mozzarella", "price": 1.00},
                    {"name": "Vegan Cheese", "price": 1.00},
                    {"name": "Parmesan", "price": 1.00},
                    {"name": "Goat Cheese", "price": 1.00},
                    {"name": "Blue Cheese", "price": 1.00},
                ],
                "veggies": [
                    {"name": "Mushrooms", "price": 0.80},
                    {"name": "Jalapeños", "price": 0.80},
                    {"name": "Spinach", "price": 0.80},
                    {"name": "Bell Peppers", "price": 0.80},
                    {"name": "Cherry Tomatoes", "price": 0.80},
                    {"name": "Onions", "price": 0.80},
                    {"name": "Olives", "price": 0.80},
                    {"name": "Artichokes", "price": 0.80},
                    {"name": "Sun-Dried Tomatoes", "price": 0.80},
                    {"name": "Arugula", "price": 0.80},
                ],
                "meats": [
                    {"name": "Pepperoni", "price": 1.50},
                    {"name": "Ham", "price": 1.50},
                    {"name": "Chicken (Grilled / Tandoori)", "price": 1.50},
                    {"name": "Bacon", "price": 1.50},
                    {"name": "Tuna", "price": 1.50},
                    {"name": "Sausage", "price": 1.50},
                ],
            },
        }
        
        self.pizza_lookup = {item['id']: item for item in self.menu_data['pizzas']}
        self.extra_lookup = {item['id']: item for item in self.menu_data['extras']}
        self.drink_lookup = {item['id']: item for item in self.menu_data['drinks']}

    def get_pizza_by_id(self, pizza_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a pizza by its ID."""
        return self.pizza_lookup.get(pizza_id.upper())

    def get_pizza_by_name(self, pizza_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a pizza by its name (case insensitive)."""
        for pizza in self.pizza_lookup.values():
            if pizza['name'].lower() == pizza_name.lower():
                return pizza
        return None

    def get_extra_by_id(self, extra_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an extra by its ID."""
        return self.extra_lookup.get(extra_id.upper())

    def get_extra_by_name(self, extra_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve an extra by its name (case insensitive)."""
        for extra in self.extra_lookup.values():
            if extra['name'].lower() == extra_name.lower():
                return extra
        return None

    def get_drink_by_id(self, drink_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a drink by its ID."""
        return self.drink_lookup.get(drink_id.upper())

    def get_drink_by_name(self, drink_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a drink by its name (case insensitive)."""
        for drink in self.drink_lookup.values():
            if drink['name'].lower() == drink_name.lower():
                return drink
        return None

    def get_topping_price(self, topping_name: str) -> Optional[float]:
        """Retrieve the price of a topping."""
        for category in self.menu_data['toppings'].values():
            for topping in category:
                if topping['name'].lower() == topping_name.lower():
                    return topping['price']
        return None

    def filter_menu_by_dietary(self, dietary_needs: str) -> Dict[str, Any]:
        """Filter the menu based on dietary needs."""
        filtered_menu = {"pizzas": [], "extras": [], "drinks": []}
        
        dietary_lower = dietary_needs.lower()
        
        # Filter pizzas based on dietary needs
        for pizza in self.menu_data['pizzas']:
            pizza_type_lower = pizza['type'].lower()
            if "vegan" in dietary_lower and "vegan" in pizza_type_lower:
                filtered_menu['pizzas'].append(pizza)
            elif "vegetarian" in dietary_lower and ("vegetarian" in pizza_type_lower or "vegan" in pizza_type_lower):
                filtered_menu['pizzas'].append(pizza)
            elif "vegan" not in dietary_lower and "vegetarian" not in dietary_lower:
                filtered_menu['pizzas'].append(pizza)

        # Filter extras based on dietary needs
        for item in self.menu_data['extras']:
            item_type_lower = item['type'].lower()
            if "vegan" in dietary_lower and "vegan" in item_type_lower:
                filtered_menu['extras'].append(item)
            elif "vegetarian" in dietary_lower and ("vegetarian" in item_type_lower or "vegan" in item_type_lower):
                filtered_menu['extras'].append(item)
            elif "vegan" not in dietary_lower and "vegetarian" not in dietary_lower:
                filtered_menu['extras'].append(item)
        
        # Drinks are always available
        filtered_menu['drinks'] = self.menu_data['drinks']
        
        return filtered_menu

    def get_menu_as_string(self, dietary_needs: Optional[str] = None) -> str:
        """Generates a formatted string of the menu, optionally filtered."""
        if dietary_needs:
            menu = self.filter_menu_by_dietary(dietary_needs)
            menu_str = f"**PizzaBahn Menu ({dietary_needs.capitalize()} Options)** \n\n"
            
            # Structured Pizzas section
            menu_str += "═══════════════════════════════════════════════════\n"
            menu_str += " **PIZZAS** \n"
            menu_str += "═══════════════════════════════════════════════════\n\n"
            
            for i, pizza in enumerate(menu['pizzas'], 1):
                menu_str += f"**{i:2d}. {pizza['name']}** - €{pizza['price']:.2f}\n"
                menu_str += f"     Type: {pizza['type']}\n"
                menu_str += f"     Description: {pizza['description']}\n\n"
            
            # Structured Extras section
            menu_str += "═══════════════════════════════════════════════════\n"
            menu_str += "**EXTRAS & SIDES** \n"
            menu_str += "═══════════════════════════════════════════════════\n\n"
            
            for i, extra in enumerate(menu['extras'], 1):
                menu_str += f"**{i:2d}. {extra['name']}** - €{extra['price']:.2f}\n"
                menu_str += f"     Type: {extra['type']}\n"
                if 'description' in extra:
                    menu_str += f"     Note: {extra['description']}\n"
                menu_str += "\n"
        else:
            menu_str = " **PizzaBahn Complete Menu** \n\n"
            
            # Group pizzas by type for better structure
            veg_pizzas = [p for p in self.menu_data['pizzas'] if 'Vegetarian' in p['type']]
            vegan_pizzas = [p for p in self.menu_data['pizzas'] if 'Vegan' in p['type']]
            nonveg_pizzas = [p for p in self.menu_data['pizzas'] if 'Non-Veg' in p['type']]
            
            # Vegetarian Pizzas
            if veg_pizzas:
                menu_str += "═══════════════════════════════════════════════════\n"
                menu_str += " **VEGETARIAN PIZZAS** \n"
                menu_str += "═══════════════════════════════════════════════════\n\n"
                for i, pizza in enumerate(veg_pizzas, 1):
                    menu_str += f"**{i:2d}. {pizza['name']}** - €{pizza['price']:.2f}\n"
                    menu_str += f"     {pizza['description']}\n\n"
            
            # Vegan Pizzas
            if vegan_pizzas:
                menu_str += "═══════════════════════════════════════════════════\n"
                menu_str += " **VEGAN PIZZAS** \n"
                menu_str += "═══════════════════════════════════════════════════\n\n"
                for i, pizza in enumerate(vegan_pizzas, 1):
                    menu_str += f"**{i:2d}. {pizza['name']}** - €{pizza['price']:.2f}\n"
                    menu_str += f"     {pizza['description']}\n\n"
            
            # Non-Veg Pizzas
            if nonveg_pizzas:
                menu_str += "═══════════════════════════════════════════════════\n"
                menu_str += " **NON-VEGETARIAN PIZZAS** \n"
                menu_str += "═══════════════════════════════════════════════════\n\n"
                for i, pizza in enumerate(nonveg_pizzas, 1):
                    menu_str += f"**{i:2d}. {pizza['name']}** - €{pizza['price']:.2f}\n"
                    menu_str += f"     {pizza['description']}\n\n"
            
            # Extras section
            menu_str += "═══════════════════════════════════════════════════\n"
            menu_str += " **EXTRAS & SIDES** \n"
            menu_str += "══════════════════════════════════════════════════\n\n"
            
            for i, extra in enumerate(self.menu_data['extras'], 1):
                menu_str += f"**{i:2d}. {extra['name']}** - €{extra['price']:.2f}\n"
                menu_str += f"     Type: {extra['type']}\n"
                if 'description' in extra:
                    menu_str += f"     Note: {extra['description']}\n"
                menu_str += "\n"
        
        # Drinks section (always the same)
        menu_str += "═══════════════════════════════════════════════════\n"
        menu_str += " **DRINKS & BEVERAGES** \n"
        menu_str += "═══════════════════════════════════════════════════\n\n"
        
        # Group drinks
        soft_drinks = [d for d in self.menu_data['drinks'] if not d['id'].startswith('B')]
        beers = [d for d in self.menu_data['drinks'] if d['id'].startswith('B')]
        
        if soft_drinks:
            menu_str += "**Soft Drinks & Water:**\n"
            for i, drink in enumerate(soft_drinks, 1):
                menu_str += f"  {i:2d}. {drink['name']} ({drink['size']}) - €{drink['price']:.2f}\n"
            menu_str += "\n"
        
        if beers:
            menu_str += "**Beer Selection:**\n"
            for i, beer in enumerate(beers, 1):
                beer_info = f"  {i:2d}. {beer['name']}"
                if 'type' in beer:
                    beer_info += f" ({beer['type']})"
                beer_info += f" ({beer['size']}) - €{beer['price']:.2f}"
                menu_str += f"{beer_info}\n"
        
        menu_str += "\n═══════════════════════════════════════════════════\n"
        menu_str += " **Tip:** Just tell me the name or number of what you'd like!\n"
        menu_str += "═══════════════════════════════════════════════════"
        
        return menu_str


class PizzaChatbot:
    def __init__(self):
        self.menu_manager = MenuManager()
        self.session_states = {}  # In-memory session state for each user
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        try:
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=self.generation_config,
                system_instruction=self._get_system_instruction()
            )
            print("PizzaChatbot initialized with Gemini model successfully")
        except Exception as e:
            print(f"Failed to initialize PizzaChatbot: {e}")
            self.model = None

    def _get_system_instruction(self) -> str:
        """Creates the detailed system instruction for the Gemini model."""
        menu_string = self.menu_manager.get_menu_as_string()

        toppings_info = """
            AVAILABLE TOPPINGS:
            **Cheese Toppings** (+€1.00 each):
            - Extra Mozzarella, Vegan Cheese, Parmesan, Goat Cheese, Blue Cheese

            **Vegetable Toppings** (+€0.80 each):
            - Mushrooms, Jalapeños, Spinach, Bell Peppers, Cherry Tomatoes, Onions, Olives, Artichokes, Sun-Dried Tomatoes, Arugula

            **Meat Toppings** (+€1.50 each):
            - Pepperoni, Ham, Chicken (Grilled/Tandoori), Bacon, Tuna, Sausage
            """
        
        instruction = f"""
            You are "PizzaBahn", a friendly and efficient pizza ordering chatbot based in Berlin, Germany.

            MENU:
            {menu_string}

            {toppings_info}

            CONVERSATION FLOW:
            1. **Greeting**: Welcome the user warmly and ask if they want to order pizza
            2. **Dietary Needs**: Ask about dietary preferences (vegan, vegetarian, halal, allergies)
            3. **Pizza Selection**: After dietary preferences, ask what pizza they'd like and offer to show menu if needed
            4. **Show Menu**: Only show menu if user asks for it or needs help choosing
            5. **Toppings**: Ask if they want additional toppings
            6. **Extras & Drinks**: Offer sides and beverages
            7. **Address**: Get their delivery address
            8. **Contact Info**: Get name and phone number
            9. **Summary**: Show complete order with total price
            10. **Confirmation**: Ask to confirm the order
            11. **Finalization**: Thank them and provide estimated delivery time

            RULES:
            - Use only English while having the conversation
            - ONLY mention items from the provided menu
            - Be concise but friendly
            - Use emojis and markdown formatting
            - After getting dietary preferences, ask what pizza they want - don't show full menu unless requested
            - When showing menu, show ONLY pizzas first, not sides and drinks
            - Only show sides and drinks when user is ready for extras
            - Guide users step by step through the ordering process
            - Calculate and show total prices
            - If user asks for unavailable items, politely suggest alternatives
            - For dietary restrictions, only show matching items
            - Always ask for confirmation before finalizing
            - We DO offer additional toppings - show the toppings list when user asks
            - When user wants toppings, show available toppings with prices and ask which ones they want
            - Calculate topping prices correctly (add to base pizza price)

            RESPONSE FORMAT:
            - Use bullet points for menu items
            - Bold important information
            - Include prices with € symbol
            - End with clear next step instruction

            Remember: You can only sell what's on the menu. No substitutions or custom items.
            """
        return instruction

    def get_session_state(self, session_id: str) -> OrderState:
        """Retrieves or creates a session state for a user."""
        if session_id not in self.session_states:
            self.session_states[session_id] = OrderState()
            print(f"Created new session state for: {session_id}")
        return self.session_states[session_id]

    def reset_session(self, session_id: str):
        """Resets the state for a given session."""
        if session_id in self.session_states:
            del self.session_states[session_id]
            print(f"Reset session state for: {session_id}")

    def extract_items_from_message(self, message: str, state: OrderState):
        """Extract pizza, extra, and drink orders from user message."""
        message_lower = message.lower()
        
        # Extract pizzas
        for pizza in self.menu_manager.pizza_lookup.values():
            if pizza['name'].lower() in message_lower:
                if pizza not in state.order_data['pizzas']:
                    state.order_data['pizzas'].append(pizza)
                    print(f" Added pizza: {pizza['name']}")

        # ADD THIS: Extract toppings
        for category in self.menu_manager.menu_data['toppings'].values():
            for topping in category:
                if topping['name'].lower() in message_lower:
                    if topping not in state.order_data['toppings']:
                        state.order_data['toppings'].append(topping)
                        print(f"Added topping: {topping['name']}")
        
        # Extract extras
        for extra in self.menu_manager.extra_lookup.values():
            if any(word in message_lower for word in extra['name'].lower().split()):
                if extra not in state.order_data['extras']:
                    state.order_data['extras'].append(extra)
                    print(f"Added extra: {extra['name']}")
        
        # Extract drinks
        for drink in self.menu_manager.drink_lookup.values():
            if drink['name'].lower() in message_lower:
                if drink not in state.order_data['drinks']:
                    state.order_data['drinks'].append(drink)
                    print(f"Added drink: {drink['name']}")

    def extract_customer_info(self, message: str, state: OrderState):
        """Extract customer information from message."""
        lines = message.split('\n')
        
        # Look for phone number pattern (FIXED - more permissive)
        if not state.order_data['customer_info']['phone']:
            # Method 1: Find any sequence of 7+ digits
            digit_matches = re.findall(r'\d{7,}', message)
            if digit_matches:
                state.order_data['customer_info']['phone'] = digit_matches[0]
                print(f"Extracted phone: {digit_matches[0]}")
            else:
                # Method 2: Find digits with some separators, then clean
                phone_match = re.search(r'[\d\s\-\(\)]{7,}', message)
                if phone_match:
                    # Keep only digits
                    phone_clean = re.sub(r'[^\d]', '', phone_match.group())
                    if len(phone_clean) >= 7:
                        state.order_data['customer_info']['phone'] = phone_clean
                        print(f"Extracted phone (cleaned): {phone_clean}")
        
        # Look for address (simple heuristic)
        if any(word in message.lower() for word in ['str', 'street', 'straße', 'platz', 'berlin']) and not state.order_data['customer_info']['address']:
            # Take the line that seems like an address
            for line in lines:
                if any(word in line.lower() for word in ['str', 'street', 'straße', 'platz']):
                    state.order_data['customer_info']['address'] = line.strip()
                    print(f"Extracted address: {line.strip()}")
                    break
        
        # Extract name (if starts with "my name is" or similar)
        name_patterns = [r'my name is (\w+)', r'i\'m (\w+)', r'name: (\w+)']
        for pattern in name_patterns:
            match = re.search(pattern, message.lower())
            if match and not state.order_data['customer_info']['name']:
                state.order_data['customer_info']['name'] = match.group(1).title()
                print(f" Extracted name: {match.group(1).title()}")
                break

    def update_state_from_message(self, message: str, state: OrderState):
        """Update order state based on user message - FIXED CONFIRMATION LOGIC"""
        message_lower = message.lower()
        
        # FIXED: Handle confirmation properly - check for confirmation words
        if state.step == "confirm_order":
            print("\n confirm_order step")
            # Check for positive confirmation
            confirmation_words = ["yes", "confirm", "ok", "correct", "place", "order", "proceed"]
            rejection_words = ["no", "wrong", "change", "modify", "cancel"]
            
            if any(word in message_lower for word in confirmation_words):
                print(f"Order confirmed by user: {message}")
                state.step = "place_order"
                return  # ADD THIS RETURN - it's already there
            elif any(word in message_lower for word in rejection_words):
                print(f"Order rejected by user: {message}")
                state.handle_order_rejection()
                return  # ADD THIS RETURN - it's already there
        
        # Extract dietary preferences
        if state.step in ["greeting", "ask_dietary"] and not state.order_data['dietary_needs']:
            if "vegan" in message_lower:
                print("\n vegan step")
                state.order_data['dietary_needs'] = "vegan"
                state.step = "ask_pizzas"
            elif "vegetarian" in message_lower:
                print("\n vegetarian step")
                state.order_data['dietary_needs'] = "vegetarian"
                state.step = "ask_pizzas"
            elif any(word in message_lower for word in ["no", "none", "meat", "everything"]):
                print("\n meat step")
                state.order_data['dietary_needs'] = "none"
                state.step = "show_menu"
        
        # Extract items from message
        self.extract_items_from_message(message, state)
        
        # Extract customer info
        self.extract_customer_info(message, state)
        
        # Update step based on what we have - IMPROVED LOGIC
        if state.step == "ask_pizzas" and state.order_data['pizzas']:
            print("\n ask_pizzas step")
            state.step = "ask_toppings"
        elif state.step == "ask_toppings":
            # Check if user wants toppings or wants to skip
            print("\n ask_toppings step")
            if any(word in message_lower for word in ["no", "none", "skip", "no thanks"]):
                state.step = "ask_pizza_preferences"
            elif state.order_data['toppings']:  # ADD THIS: if toppings were added, move forward
                state.step = "ask_pizza_preferences"
            # If they mentioned toppings but didn't specify, stay in ask_toppings 
        elif state.step == "ask_pizza_preferences":
            print("\n ask_pizza_preferences step")
            state.step = "ask_sides_extras"
        elif state.step == "ask_sides_extras":
            print("\n ask_sides_extras step")
            state.step = "ask_drinks"
        elif state.step == "ask_drinks":
            print("\n ask_drinks step")
            state.step = "ask_address"    
        elif state.step == "ask_address" and state.order_data['customer_info']['address']:
            print("\n ask_address step")
            state.step = "ask_contact_info"
        elif state.step == "ask_contact_info":
            print(f"\n ask_contact_info step - checking info:")
            print(f"  Name: {state.order_data['customer_info']['name']}")
            print(f"  Phone: {state.order_data['customer_info']['phone']}")
            
            # FIXED: Check if we have both name and phone after extraction
            if (state.order_data['customer_info']['name'] and 
                state.order_data['customer_info']['phone']):
                print("\n Both name and phone collected - moving to show_summary")
                state.step = "show_summary"
            else:
                print("\n Still missing contact info - staying in ask_contact_info")



    def calculate_total_price(self, state: OrderState) -> float:
        """Calculate the total price of the order."""
        total = 0.0
        
        # Add pizza prices
        for pizza in state.order_data['pizzas']:
            total += pizza['price']
        
        # Add extra prices
        for extra in state.order_data['extras']:
            total += extra['price']
        
        # Add drink prices
        for drink in state.order_data['drinks']:
            total += drink['price']
        
        # Add topping prices
        for topping in state.order_data['toppings']:
            if isinstance(topping, dict) and 'price' in topping:
                total += topping['price']
            elif isinstance(topping, str):
                # Look up topping price
                topping_price = self.menu_manager.get_topping_price(topping)
                if topping_price:
                    total += topping_price
        
        return round(total, 2)

    def process_conversation(self, conversation_history: List[Dict[str, str]], user_message: str, session_id: str) -> Dict[str, Any]:
        """Main conversation processing method."""
        if not self.model:
            return {'content': "Sorry, I'm currently unavailable. Please try again later.", 'type': 'text'}
        
        state = self.get_session_state(session_id)
        
        # Handle special commands
        if "restart" in user_message.lower() or "cancel" in user_message.lower():
            self.reset_session(session_id)
            return {'content': "Order cancelled! Let's start fresh. Welcome to PizzaBahn! Would you like to order a delicious pizza today?", 'type': 'text'}
        
        # Handle menu request properly
        if "menu" in user_message.lower() or "show menu" in user_message.lower():
            print(f"🍕 Menu requested by session {session_id}")
            # Get current dietary preferences if any
            dietary_needs = state.order_data.get('dietary_needs')
            menu_text = self.menu_manager.get_menu_as_string(dietary_needs)
            
            # Update state to show menu has been displayed
            if state.step in ["greeting", "ask_dietary"]:
                state.step = "ask_pizzas"
                state.has_shown_menu = True
            
            return {'content': menu_text, 'type': 'menu'}
        
        # IMPORTANT: Update state BEFORE generating response
        print(f"Current step before update: {state.step}")
        self.update_state_from_message(user_message, state)
        print(f"Current step after update: {state.step}")
        
        # Create context for the model
        context = f"""
            Current Step: {state.step}
            Order Status:
            - Dietary Needs: {state.order_data.get('dietary_needs', 'Not specified')}
            - Pizzas: {[p['name'] for p in state.order_data['pizzas']]}
            - Extras: {[e['name'] for e in state.order_data['extras']]}
            - Drinks: {[d['name'] for d in state.order_data['drinks']]}
            - Address: {state.order_data['customer_info'].get('address', 'Not provided')}
            - Name: {state.order_data['customer_info'].get('name', 'Not provided')}
            - Phone: {state.order_data['customer_info'].get('phone', 'Not provided')}

            User Message: {user_message}

            IMPORTANT INSTRUCTIONS:
            - If step is "place_order", the user has confirmed their order. Generate a completion message with order details and delivery time.
            - If step is "show_summary", show the complete order summary and ask for confirmation.
            - If step is "confirm_order", ask the user to confirm their order (yes/no).
            - Follow the current step to provide appropriate response.

            Based on the current step and order status, provide an appropriate response to guide the customer through the ordering process.
            """
        
        try:
            print(f"Processing message for session {session_id}, step: {state.step}")
            
            # If we need to show summary, calculate total
            if state.step in ["show_summary", "confirm_order"]:
                print("\n show_summary step")
                total = self.calculate_total_price(state)
                context += f"\nCalculated Total: €{total:.2f}"
                state.order_data['total_price'] = total
            
            response = self.model.generate_content(context)
            response_text = response.text
            
            # If order is complete, add JSON output and mark as complete
            if state.step == "place_order":
                order_json = {
                    "order_id": str(uuid.uuid4())[:8],
                    "timestamp": datetime.datetime.now().isoformat(),
                    "customer": state.order_data['customer_info'],
                    "items": {
                        "pizzas": state.order_data['pizzas'],
                        "extras": state.order_data['extras'],
                        "drinks": state.order_data['drinks'],
                        "toppings": state.order_data['toppings']
                    },
                    "total": state.order_data['total_price'],
                    "status": "confirmed"
                }
                response_text += f"\n\n```json\n{json.dumps(order_json, indent=2)}\n```"
                state.step = "end_conversation"
                print(f"Order completed for session {session_id}")
            
            # If showing summary, move to confirm_order step
            elif state.step == "show_summary":
                state.step = "confirm_order"
            
            return {'content': response_text, 'type': 'text'}
            
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return {'content': "Sorry, I'm having trouble processing your request. Please try again!", 'type': 'text'}

chatbot = PizzaChatbot()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        print(f"📨 Received message from session {session_id}: {user_message[:50]}...")

        if not user_message:
            return jsonify({'response': "Please provide a message.", 'type': 'text'}), 400

        result = chatbot.process_conversation(conversation_history, user_message, session_id)
        
        return jsonify({
            'response': result['content'],
            'type': result['type'],
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"Flask route error: {e}")
        return jsonify({
            'response': "Sorry, I'm having technical difficulties. Please try again!",
            'type': 'text'
        }), 500

@app.route('/api/menu', methods=['GET'])
def get_menu():
    try:
        return jsonify({
            'menu_data': chatbot.menu_manager.menu_data,
            'type': 'menu'
        })
    except Exception as e:
        print(f"Menu endpoint error: {e}")
        return jsonify({'error': 'Failed to retrieve menu data'}), 500

@app.route('/api/reset/<session_id>', methods=['POST'])
def reset_session_endpoint(session_id):
    try:
        chatbot.reset_session(session_id)
        return jsonify({'message': 'Session reset successfully'})
    except Exception as e:
        print(f"Reset endpoint error: {e}")
        return jsonify({'error': 'Failed to reset session'}), 500

if __name__ == '__main__':
    print("Starting PizzaBahn server...")

    app.run(debug=True, port=5000)
