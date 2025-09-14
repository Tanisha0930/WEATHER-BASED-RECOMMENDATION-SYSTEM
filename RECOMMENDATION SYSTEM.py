import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from itertools import combinations
from functools import lru_cache
import json
import os
import requests
from bs4 import BeautifulSoup

# --- File I/O ---
WARDROBE_FILE = "wardrobe.json"

def load_wardrobe():
    if os.path.exists(WARDROBE_FILE):
        with open(WARDROBE_FILE, "r") as f:
            return json.load(f)
    return {'tops': {}, 'bottoms': {}, 'outers': {}}

def save_wardrobe():
    with open(WARDROBE_FILE, "w") as f:
        json.dump(wardrobe, f, indent=4)

# --- Wardrobe & Graph ---
wardrobe = load_wardrobe()
compatibility_graph = {}

def build_graph():
    compatibility_graph.clear()
    all_items = []
    for cat, items in wardrobe.items():
        for name, data in items.items():
            compatibility_graph[name] = []
            all_items.append((cat, name, data))

    for (cat1, name1, data1), (cat2, name2, data2) in combinations(all_items, 2):
        if data1['style'] == data2['style'] or data1['color'] == data2['color']:
            compatibility_graph[name1].append(name2)
            compatibility_graph[name2].append(name1)

# --- GUI: Add Item ---
def add_item(category):
    name = simpledialog.askstring("Item Name", f"Enter {category[:-1].capitalize()} name:")
    if not name: return
    color = simpledialog.askstring("Color", "Enter color:")
    style = simpledialog.askstring("Style", "Enter style (casual/formal):")
    weather = simpledialog.askstring("Weather", "Enter suitable weather (sunny/cold/both):")

    gender = simpledialog.askstring("Gender", "Enter gender (male/female/other):")
    if gender:
        gender = gender.lower()
        if gender not in ['male', 'female', 'other']:
            messagebox.showerror("Invalid Input", "Please enter gender as male, female, or other.")
            return
    else:
        messagebox.showerror("Missing Info", "Gender is required.")
        return

    if not all([name, color, style, weather]):
        messagebox.showerror("Missing Info", "All fields must be filled.")
        return

    wardrobe[category][name] = {
        'color': color.lower(),
        'style': style.lower(),
        'weather': ["sunny", "cold"] if weather.lower() == "both" else [weather.lower()]
    }
    save_wardrobe()
    messagebox.showinfo("Added", f"{name} added to {category}.")

# --- Filtering ---
def filter_items(weather, style):
    filtered = {'tops': [], 'bottoms': [], 'outers': []}
    for cat, items in wardrobe.items():
        for item, props in items.items():
            if weather in props['weather'] and props['style'] == style:
                filtered[cat].append(item)
    return filtered

# --- DP Scoring ---
@lru_cache(maxsize=None)
def score_outfit(top, bottom, outer):
    items = [top, bottom] + ([outer] if outer else [])
    colors, styles = [], []
    for item in items:
        for cat, items_dict in wardrobe.items():
            if item in items_dict:
                colors.append(items_dict[item]['color'])
                styles.append(items_dict[item]['style'])
    return (3 - len(set(colors))) + (3 - len(set(styles)))

# --- Backtracking ---
def backtrack_outfits(filtered, path=None, used=None, results=None):
    if path is None:
        path = []
    if used is None:
        used = set()
    if results is None:
        results = []

    if len(path) == 2 or (len(path) == 3 and filtered['outers']):
        top, bottom = path[0], path[1]
        outer = path[2] if len(path) == 3 else None
        score = score_outfit(top, bottom, outer)
        results.append((path.copy(), score))
        return

    next_cat = ['tops', 'bottoms', 'outers'][len(path)]
    for item in filtered[next_cat]:
        if item not in used:
            if not path or all(item in compatibility_graph.get(p, []) for p in path):
                used.add(item)
                path.append(item)
                backtrack_outfits(filtered, path, used, results)
                path.pop()
                used.remove(item)

# --- Fetch Fashion Ideas from Who What Wear ---
def fetch_fashion_ideas():
    url = "https://www.whowhatwear.com/fashion/outfit-ideas"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extracting outfit idea titles
        outfit_titles = []
        for title in soup.find_all("h2"):
            outfit_titles.append(title.text.strip())
        return outfit_titles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching fashion ideas: {e}")
        return []

# --- Recommendation Logic ---
def recommend():
    city_name = simpledialog.askstring("City Name", "Enter your city:")
    if not city_name:
        messagebox.showerror("Input Error", "City name is required.")
        return

    weather_condition, temperature = get_current_weather(city_name)
    if weather_condition is None:
        messagebox.showerror("API Error", "Could not fetch weather data.")
        return

    if weather_condition in ['clear', 'sunny']:
        weather_category = 'sunny'
    elif weather_condition in ['rain', 'snow', 'clouds']:
        weather_category = 'cold'
    else:
        weather_category = 'sunny'

    style = style_var.get()
    if not style:
        messagebox.showerror("Input Error", "Please select a style.")
        return

    build_graph()
    filtered = filter_items(weather_category, style)
    results = []
    backtrack_outfits(filtered, [], set(), results)

    results.sort(key=lambda x: -x[1])
    output_box.delete("1.0", tk.END)

    # Show weather information
    output_box.insert(tk.END, f"Weather in {city_name}:\n")
    output_box.insert(tk.END, f"Condition: {weather_condition.capitalize()}\n")
    output_box.insert(tk.END, f"Temperature: {temperature}°C\n\n")

    if not results:
        output_box.insert(tk.END, "No matching outfits found.")
    else:
        output_box.insert(tk.END, f"Top Outfit Recommendations for {city_name} ({weather_condition}, {temperature}°C):\n\n")
        for i, (outfit, score) in enumerate(results[:3], 1):
            output_box.insert(tk.END, f"{i}. {' + '.join(outfit)} (Score: {score})\n")
    
    # Fetch fashion inspiration ideas from the web
    outfit_ideas = fetch_fashion_ideas()
    output_box.insert(tk.END, "\n\nFashion Inspiration Ideas:\n")
    if outfit_ideas:
        for i, idea in enumerate(outfit_ideas[:3], 1):  # Display top 3 ideas
            output_box.insert(tk.END, f"{i}. {idea}\n")
    else:
        output_box.insert(tk.END, "No fashion ideas found.\n")

# --- Weather API ---
def get_current_weather(city_name):
    api_key = '2ebb7168ae969dc64418653775bc7227'  # Your API Key
    base_url = 'https://api.openweathermap.org/data/2.5/weather'
    params = {
        'q': city_name,
        'appid': api_key,
        'units': 'metric'
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        weather_condition = data['weather'][0]['main'].lower()
        temperature = data['main']['temp']
        return weather_condition, temperature
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None, None

# --- GUI Layout ---
root = tk.Tk()
root.title("Outfit Recommender (Weather + DAA + GUI)")
root.geometry("600x600")

tk.Label(root, text="Outfit Recommender (DP + Graph + Backtracking + API)", font=("Arial", 14, "bold")).pack(pady=10)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)
tk.Button(btn_frame, text="Add Top", command=lambda: add_item('tops')).grid(row=0, column=0, padx=5)
tk.Button(btn_frame, text="Add Bottom", command=lambda: add_item('bottoms')).grid(row=0, column=1, padx=5)
tk.Button(btn_frame, text="Add Outer", command=lambda: add_item('outers')).grid(row=0, column=2, padx=5)

select_frame = tk.Frame(root)
select_frame.pack(pady=15)
tk.Label(select_frame, text="Style:").grid(row=0, column=0)
style_var = tk.StringVar()
ttk.Combobox(select_frame, textvariable=style_var, values=["casual", "formal"]).grid(row=0, column=1)

tk.Label(select_frame, text="Gender:").grid(row=0, column=2)
gender_var = tk.StringVar()
ttk.Combobox(select_frame, textvariable=gender_var, values=["Male", "Female", "Other"]).grid(row=0, column=3, padx=5)

tk.Button(root, text="Recommend Outfits", command=recommend, bg="#cceeff").pack(pady=10)

output_box = tk.Text(root, width=70, height=18, wrap=tk.WORD)
output_box.pack(pady=15)

root.mainloop()
