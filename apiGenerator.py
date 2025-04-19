import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import openai

# --- Spoonacular API Key ---
API_KEY = st.secrets["SPOONACULAR_API_KEY"]
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Helper Functions ---
def get_recipes_by_ingredients(ingredients, number=5):
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    params = {
        "ingredients": ",".join(ingredients),
        "number": number,
        "ranking": 1,
        "ignorePantry": True,
        "apiKey": API_KEY
    }
    response = requests.get(url, params=params)
    try:
        return response.json()
    except:
        return []

def get_recipe_info(recipe_id):
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {"apiKey": API_KEY, "includeNutrition": True}
    response = requests.get(url, params=params)
    try:
        return response.json()
    except:
        return {}

def download_favorites_text(favorites):
    lines = []
    for recipe in favorites:
        lines.append(f"{recipe['title']}\n{recipe['image']}\n")
    return "\\n".join(lines)

def render_instructions(raw_html):
    if not raw_html:
        st.write("No instructions available.")
        return

    soup = BeautifulSoup(raw_html, "html.parser")
    plain_text = soup.get_text(separator=" ")
    sentences = [s.strip() for s in plain_text.split(".") if s.strip()]
    st.markdown("**Instructions:**")
    for sentence in sentences:
        st.markdown(f"- {sentence}.")

# --- Session State ---
if "favorites" not in st.session_state:
    st.session_state.favorites = []
if "trigger_search" not in st.session_state:
    st.session_state.trigger_search = False

# --- Sidebar ---
st.sidebar.title("Ingredient Search")
st.sidebar.markdown("Customize your recipe search")

keyword_input = st.sidebar.text_input("Enter ingredients (comma-separated):", "chicken, rice")
ingredient_selection = [i.strip().lower() for i in keyword_input.split(",") if i.strip()]
num_results = st.sidebar.slider("Number of Recipes", 1, 10, 5)

# --- MAIN APP ---
st.title("AI-Powered Recipe Generator")
st.write("Find recipes using the ingredients you have.")
# --- AI Cooking Assistant ---
st.markdown("## Ask the Cooking Assistant")
user_input = st.text_input("Ask a cooking question (e.g., What can I substitute for eggs?)")
if user_input:
    with st.spinner("Thinking..."):
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful home cooking assistant. Be concise and friendly."},
                    {"role": "user", "content": user_input}
                ]
            )
            answer = response.choices[0].message.content
            st.markdown(f"**Assistant:** {answer}")
        except Exception as e:
            st.error("Something went wrong. Please check your API key or try again later.")
            st.text(str(e))

if st.sidebar.button("Find Recipes", key="find_recipes") and ingredient_selection:
    st.session_state.recipes = get_recipes_by_ingredients(ingredient_selection, number=num_results)

if "recipes" in st.session_state and st.session_state.recipes:
    for recipe in st.session_state.recipes:
        if isinstance(recipe, dict) and 'image' in recipe:
            st.markdown("---")
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.image(recipe['image'], width=150)
            
            with col2:
                st.subheader(recipe.get('title', 'No Title'))
                st.write(f"**Used:** {', '.join(i['name'] for i in recipe.get('usedIngredients', []))}")
                st.write(f"**Missing:** {', '.join(i['name'] for i in recipe.get('missedIngredients', []))}")
                
                fav_key = f"fav_{recipe['id']}"
                if fav_key not in st.session_state:
                    st.session_state[fav_key] = False
                
                if not st.session_state[fav_key]:
                    if st.button("Save to Favorites", key=f"save_{recipe['id']}"):
                        st.session_state.favorites.append(recipe)
                        st.session_state[fav_key] = True
                        st.success("Added to favorites!")
                else:
                    if st.button("Remove from Favorites", key=f"remove_{recipe['id']}"):
                        st.session_state.favorites = [
                            r for r in st.session_state.favorites if r['id'] != recipe['id']
                        ]
                        st.session_state[fav_key] = False
                        st.warning("Removed from Favorites")
            
            with st.expander("Show Recipe & Nutrition Info"):
                details = get_recipe_info(recipe['id'])
                url = details.get("sourceUrl", "")
                if url:
                    st.markdown(
                        f'<a href="{url}" target="_blank">'
                        f'<button style="background-color:#4CAF50; color:white; padding:8px 16px; '
                        f'border:none; border-radius:5px; font-size:16px; cursor:pointer;">'
                        f'View Full Recipe</button></a>',
                        unsafe_allow_html=True
                    )
                else:
                    st.write("No recipe website available.")
                
                if "nutrition" in details:
                    st.write("**Nutrition (per serving):**")
                    for n in details["nutrition"]["nutrients"][:5]:
                        st.write(f"{n.get('name', 'N/A')}: {n.get('amount', '?')} {n.get('unit', '')}")
elif st.session_state.trigger_search:
    st.warning("No recipes found. Try different ingredients.")
elif not ingredient_selection:
    st.sidebar.warning("Please select at least one ingredient.")


# --- Favorite Recipes ---
st.markdown("## Favorite Recipes")
if st.session_state.favorites:
    for fav in st.session_state.favorites:
        with st.expander(fav['title']):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(fav['image'], width=100)
            with col2:
                details = get_recipe_info(fav['id'])
                url = details.get("sourceUrl", "")
                if url:
                    st.markdown(
                        f'<a href="{url}" target="_blank">'
                        f'<button style="background-color:#4CAF50; color:white; padding:6px 12px; '
                        f'border:none; border-radius:5px; font-size:14px; cursor:pointer;">'
                        f'View Full Recipe'
                        f'</button></a>',
                        unsafe_allow_html=True
                    )
                else:
                    st.write("No external recipe link available.")
    txt_data = download_favorites_text(st.session_state.favorites)
    st.download_button("Download Favorites", txt_data, file_name="favorite_recipes.txt")
else:
    st.info("No favorite recipes saved yet.")
