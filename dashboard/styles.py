import streamlit as st

def apply_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Main Container */
        .main {
            background: radial-gradient(circle at top left, #1a1a2e, #16213e, #0f3460);
            color: #ffffff;
        }

        /* Glassmorphism Card */
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            margin-bottom: 20px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .glass-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        /* Metrics */
        .metric-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #4ecca3;
        }

        .metric-label {
            font-size: 0.9rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Status Badge */
        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .status-success { background: rgba(78, 204, 163, 0.2); color: #4ecca3; border: 1px solid #4ecca3; }
        .status-pending { background: rgba(255, 184, 76, 0.2); color: #ffb84c; border: 1px solid #ffb84c; }
        .status-failed { background: rgba(233, 69, 96, 0.2); color: #e94560; border: 1px solid #e94560; }

        /* Custom Button */
        .stButton>button {
            background: linear-gradient(90deg, #4ecca3, #45b796);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
        }

        .stButton>button:hover {
            opacity: 0.9;
            box-shadow: 0 4px 12px rgba(78, 204, 163, 0.4);
        }

        /* Title Styling */
        .premium-title {
            background: linear-gradient(90deg, #ffffff, #4ecca3);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
        }

        .premium-subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }

        /* Image styling */
        .product-img {
            border-radius: 10px;
            margin-bottom: 15px;
            object-fit: contain;
            background: white;
            padding: 5px;
        }
        
        /* Confidence Bar */
        .confidence-container {
            width: 100%;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            height: 6px;
            margin-top: 10px;
        }
        
        .confidence-bar {
            height: 100%;
            border-radius: 10px;
            background: linear-gradient(90deg, #4ecca3, #45b796);
        }
        </style>
    """, unsafe_allow_html=True)

def card_container(title, content, image_url=None, confidence=None, url=None, platform=None):
    conf_pct = int(confidence * 100) if confidence else 0
    platform_label = platform.replace("_", " ").title() if platform else ""
    
    html = f"""
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <span class="status-badge {'status-success' if conf_pct > 70 else 'status-pending'}">{platform_label}</span>
            {f'<span style="font-size: 0.8rem; color: #4ecca3; font-weight: 600;">{conf_pct}% Match</span>' if confidence else ''}
        </div>
        <h4 style="margin: 15px 0 10px 0; font-size: 1.1rem; line-height: 1.4; height: 3em; overflow: hidden;">{title}</h4>
        {f'<img src="{image_url}" class="product-img" width="100%" height="150">' if image_url else ''}
        <div class="metric-container">
            <div>
                <div class="metric-label">Best Price</div>
                <div class="metric-value" style="font-size: 1.5rem;">{content}</div>
            </div>
        </div>
        {f'<div class="confidence-container"><div class="confidence-bar" style="width: {conf_pct}%"></div></div>' if confidence else ''}
        {f'<a href="{url}" target="_blank" style="text-decoration: none;"><div style="margin-top: 15px; padding: 8px; text-align: center; background: rgba(78, 204, 163, 0.1); border: 1px solid rgba(78, 204, 163, 0.3); border-radius: 5px; color: #4ecca3; font-size: 0.9rem; font-weight: 600;">View Product</div></a>' if url else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
