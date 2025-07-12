# pytrends for Google Trends data
# requests for HTTP requests to SerpAPI for search volume and competition

import time
import requests
from pytrends.request import TrendReq
import google.generativeai as genai

# --- CONFIGURATION ---
GEMINI_API_KEY = "GOOGLE_API_KEY_HERE"
SERPAPI_KEY = "SERPAPI_KEY_HERE"

# --- Initialize Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-flash")


# --- Generate Keywords using Gemini with a prompt of low competition, high volume ---
def generate_keywords_with_gemini(seed_keyword, num_keywords=100):
    prompt = f"""
    Generate a list of {num_keywords} keyword ideas related to '{seed_keyword}'.
    Focus on low competition, and moderate to high search volume SEO keywords.
    Return the keywords as a comma-separated list only. No explanations, no numbering.
    """
    response = gemini_model.generate_content(prompt)
    text = response.text
    keywords = [kw.strip() for kw in text.replace("\n", ",").split(",") if kw.strip()]
    return list(set(keywords))  # Remove duplicates


# --- Google Trends score using pytrends ---
def get_trend_score(keyword):
    pytrends = TrendReq(hl="en-US", tz=330)  # IST timezone
    try:
        pytrends.build_payload(
            [keyword], cat=0, timeframe="today 12-m", geo="", gprop=""
        )
        data = pytrends.interest_over_time()
        if not data.empty:
            return int(data[keyword].mean())
        else:
            return 0
    except:
        return 0


# --- SerpAPI: Get search volume and competition ---
def get_keyword_metrics(keyword):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": keyword,
        "api_key": SERPAPI_KEY,
        "google_domain": "google.com",
        "gl": "in",
        "hl": "en",
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        monthly_search_volume = data.get("search_information", {}).get(
            "total_results", 0
        )
        competition = len(data.get("organic_results", []))
        return {"search_volume": monthly_search_volume, "competition": competition}
    except Exception as e:
        print(f" Error fetching SerpAPI data for '{keyword}': {e}")
        return {"search_volume": 0, "competition": 999}


# --- Ask Gemini if keyword is easy to rank ---
def is_easy_to_rank(keyword):
    try:
        prompt = f"Would the keyword '{keyword}' be easy to rank for on Google's first page? Just answer YES or NO."
        response = gemini_model.generate_content(prompt)
        answer = response.text.strip().lower()
        return "yes" in answer
    except:
        return False


# --- Main Pipeline ---
def seo_keyword_research_pipeline(seed_keyword):
    print(f"\n Generating keyword ideas using Gemini for seed: '{seed_keyword}'")
    keywords = generate_keywords_with_gemini(seed_keyword, num_keywords=120)
    print(f" {len(keywords)} keywords generated.\n")

    keyword_metrics = []

    print(" Fetching SEO metrics and trend scores...")
    for i, kw in enumerate(keywords):
        trend_score = get_trend_score(kw)
        serp = get_keyword_metrics(kw)
        rankable = is_easy_to_rank(kw)

        keyword_metrics.append(
            {
                "keyword": kw,
                "trend_score": trend_score,
                "search_volume": serp["search_volume"],
                "competition": serp["competition"],
                "rankable": rankable,
            }
        )

        print(
            f"{i + 1:03}) {kw} | Trend: {trend_score}, Volume: {serp['search_volume']}, Comp: {serp['competition']}, Rankable: {rankable}"
        )
        time.sleep(1.2)  # delay to avoid rate limits

    #  Filter: Must be Gemini-approved + volume > 10000 + low competition
    filtered = [
        k
        for k in keyword_metrics
        if k["rankable"] and k["search_volume"] > 10000 and k["competition"] < 10
    ]

    print(f"\n Filtered down to {len(filtered)} strong keywords")

    #  Sort: high volume, low competition, high trend
    top_keywords = sorted(
        filtered,
        key=lambda x: (-x["search_volume"], x["competition"], -x["trend_score"]),
    )[:50]

    print("\n Top Most 50 SEO-Optimized Keywords:")
    for i, kw in enumerate(top_keywords, 1):
        print(
            f"{i:02}. {kw['keyword']} | Volume: {kw['search_volume']} | Comp: {kw['competition']} | Trend: {kw['trend_score']}"
        )

    return top_keywords


# --- Main ---
if __name__ == "__main__":
    seed = input("Enter your seed keyword: ")
    seo_keyword_research_pipeline(seed)
