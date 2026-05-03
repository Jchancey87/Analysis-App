import base64
import logging
from openai import OpenAI
from config import Config

log = logging.getLogger(__name__)

VISION_SYSTEM = """
You are an expert Technical Analyst.
I am providing you with a highly detailed 4-panel intraday session chart for a specific ticker.
This chart includes pre-market, regular hours, and post-market data for the given date.

Panel Breakdown:
1. Main Price Panel: Candlesticks with an EMA Ribbon (spans 8, 13, 21, 34, 55).
2. Volume Panel (below price): Shows trading volume and a Relative Volume (RVOL) line (magenta).
3. ADX Panel: Shows trend strength (ADX in white) and directional movement (+DI green, -DI red).
4. ATR Panel: Shows volatility (Average True Range).

Please analyze this session chart and provide a concise technical summary.
Focus on:
1. Intraday price action structure (gap, morning push, afternoon fade, etc.).
2. Significant volume anomalies and RVOL spikes.
3. Trend strength (ADX) and volatility shifts (ATR).
4. Overall technical verdict (Bullish, Bearish, Neutral) for the session.

Keep your response structured, concise, and focused purely on the price action and indicators visible in the chart.
"""

def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_charts_multi_tf(ticker: str, image_paths: list[str]) -> str | None:
    """
    Takes a list of local image paths, converts them to base64, and sends them to 
    an OpenAI-compatible Vision API (e.g. GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro).
    Returns None if VISION_API_KEY is not set or if an error occurs.
    """
    if not Config.VISION_API_KEY:
        log.warning("VISION_API_KEY not set. Skipping vision analysis.")
        return None

    try:
        client = OpenAI(
            api_key=Config.VISION_API_KEY,
            base_url=Config.VISION_BASE_URL
        )
        
        content = [
            {"type": "text", "text": f"Here is the detailed intraday session chart for {ticker}. Please analyze it based on the 4 panels provided."}
        ]
        
        for path in image_paths:
            base64_image = _encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })

        response = client.chat.completions.create(
            model=Config.VISION_MODEL,
            messages=[
                {"role": "system", "content": VISION_SYSTEM},
                {"role": "user", "content": content}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        log.error(f"Error calling Vision API: {e}")
        return None
