"""
PriceAgent Pro — Streamlit Dashboard
Run: streamlit run dashboard/app.py
"""

import sys
import os
import asyncio
import threading
import queue
import io
import re
import time
import streamlit as st



if sys.platform == 'win32':
    # Required for Playwright subprocesses on Windows.
    # We suppress the DeprecationWarning as this is still necessary for sync Playwright in threads.
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())



ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import ProductMatchingAgent
from dashboard.styles import apply_styles

st.set_page_config(
    page_title="PriceAgent Pro",
    page_icon="🎯",
    layout="wide",
)
apply_styles()


PLATFORM_META = {
    "amazon": {
        "name": "Amazon",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
        "color": "#FF9900",
    },
    "flipkart": {
        "name": "Flipkart",
        "icon": "https://static-assets-web.flixcart.com/batman-returns/batman-returns/p/images/fkheaderlogo_exploreplus-54401f.svg",
        "color": "#2874F0",
    },
    "croma": {
        "name": "Croma",
        "icon": "https://media.croma.com/image/upload/v1637759004/Croma%20Assets/CMS/Category%20Icon/Mobiles_n07s2u.png",
        "color": "#6CC04A",
    },
    "reliance_digital": {
        "name": "Reliance Digital",
        "icon": "https://www.reliancedigital.in/build/client/images/rdl-logo.svg",
        "color": "#E31E25",
    },
}


class Tee(io.StringIO):
    """Duplicates stdout to both a buffer and the original terminal."""
    def __init__(self, buffer, original_stdout):
        super().__init__()
        self.buffer = buffer
        self.original_stdout = original_stdout

    def write(self, s):
        self.buffer.write(s)
        self.original_stdout.write(s)
        self.original_stdout.flush()

    def getvalue(self):
        return self.buffer.getvalue()

def run_agent_in_thread(url: str, result_queue: queue.Queue, stream_queue: queue.Queue):

    """Run the agent in a daemon thread; push result to queue."""
    try:
        agent = ProductMatchingAgent(headless=False)
        def stream_cb(p_name, m):
            stream_queue.put((p_name, m))
        result = agent.run(url, callback=stream_cb)
        result_queue.put(("ok", result))
    except Exception as e:
        result_queue.put(("error", str(e)))


def render_platform_card(platform: str, match: dict | None, is_source: bool = False):
    meta = PLATFORM_META.get(platform, {"name": platform.title(), "color": "#888"})
    name = meta["name"]
    color = meta["color"]

    if match:
        conf_pct = int(match["confidence"] * 100)
        badge = "✅ Source" if is_source else f"✅ {conf_pct}% match"
        badge_bg = "#e8f5e9" if is_source else "#e3f2fd"
        badge_color = "#1b5e20" if is_source else "#0d47a1"

        st.markdown(f"""
        <div class="glass-card" style="border-top: 3px solid {color};">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h4 style="margin:0; color:{color};">{name}</h4>
                <span style="background:{badge_bg}; color:{badge_color};
                      padding:3px 10px; border-radius:12px; font-size:12px;
                      font-weight:600;">{badge}</span>
            </div>
            <a href="{match['url']}" target="_blank" style="text-decoration:none;">
                <div style="padding:11px; background:{color}; border-radius:8px;
                     color:white; font-weight:700; font-size:0.95rem;
                     text-align:center; letter-spacing:0.3px;">
                    View on {name} →
                </div>
            </a>
            <div style="margin-top:10px; font-size:11px; color:#888;
                 word-break:break-all;">{match['url']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="glass-card" style="border-top: 3px solid #555; opacity:0.65;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h4 style="margin:0; color:#aaa;">{name}</h4>
                <span style="background:#fbe9e7; color:#b71c1c;
                      padding:3px 10px; border-radius:12px; font-size:12px;
                      font-weight:600;">❌ Not found</span>
            </div>
            <div style="padding:11px; background:#333; border-radius:8px;
                 color:#888; font-size:0.9rem; text-align:center;">
                Product not available or listing not matched
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── UI ──────────────────────────────────────────────────────────────────────

st.markdown('<h1 class="premium-title">PriceAgent Pro</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="premium-subtitle">Paste any mobile product link from Amazon, '
    'Flipkart, Croma, or Reliance Digital — we find the same product on the rest.</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 🎯 PriceAgent Pro")
    st.markdown("---")
    target_url = st.text_input(
        "Product URL",
        placeholder="https://www.amazon.in/dp/...",
        help="Paste a product link from Amazon, Flipkart, Croma, or Reliance Digital",
    )
    search_button = st.button("🔍 Find on All Platforms", use_container_width=True)
    st.markdown("---")
    st.info(
        "💡 **Tip:** For best results, use the full product page URL "
        "(not a search results page)."
    )
    st.markdown("**Supported platforms:**")
    for meta in PLATFORM_META.values():
        st.markdown(f"• {meta['name']}")

# ── Main logic ──────────────────────────────────────────────────────────────

if search_button and target_url:
    # Basic URL validation
    target_url = target_url.strip()
    supported = ["amazon.in", "flipkart.com", "croma.com", "reliancedigital.in"]
    if not any(s in target_url for s in supported):
        st.error("❌ Please paste a URL from Amazon, Flipkart, Croma, or Reliance Digital.")
        st.stop()

    st.markdown("---")

    with st.status("🚀 PriceAgent Pro is running...", expanded=True) as status:
        status.write("🌐 Launching browser and fetching product details...")

        # Setup log capture (Tee duplicates to terminal)
        log_buffer = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = Tee(log_buffer, old_stdout)


        result_q: queue.Queue = queue.Queue()
        stream_q: queue.Queue = queue.Queue()
        t = threading.Thread(
            target=run_agent_in_thread,
            args=(target_url, result_q, stream_q),
            daemon=True,
        )
        t.start()

        # Poll until done, showing results as they come in
        placeholder = st.empty()
        log_expander = st.expander("📄 View Live Search Logs", expanded=False)
        log_placeholder = log_expander.empty()
        
        if "partial_matches" not in st.session_state:
            st.session_state["partial_matches"] = {}
        
        # Container for real-time results display
        results_container = st.container()
        results_area = results_container.empty()

        dots = 0
        while t.is_alive():
            dots = (dots + 1) % 4
            placeholder.markdown(f"⏳ Searching all platforms{'.' * dots}")
            
            # Check for streamed results
            new_data = False
            while not stream_q.empty():
                p_name, match = stream_q.get()
                st.session_state["partial_matches"][p_name] = match
                new_data = True
            
            if new_data:
                # Update the results area in real-time
                with results_area:
                    st.markdown("### ⚡ Live Matching Results")
                    live_cols = st.columns(4)
                    for idx, p_n in enumerate(["amazon", "flipkart", "croma", "reliance_digital"]):
                        with live_cols[idx]:
                            m = st.session_state["partial_matches"].get(p_n)
                            render_platform_card(p_n, m)

            # Update log view
            log_placeholder.code(log_buffer.getvalue())
            time.sleep(0.5)
        
        # Final log update
        sys.stdout = old_stdout
        log_placeholder.code(log_buffer.getvalue())
        placeholder.empty()

        outcome, payload = result_q.get()

        if outcome == "error":
            status.update(label="❌ Critical Agent Error", state="error")
            st.error(f"The agent thread crashed: {payload}")
            st.stop()

        results = payload
        if not isinstance(results, dict):
            status.update(label="❌ Invalid payload", state="error")
            st.error(f"Agent returned invalid data type: {type(results)}")
            st.stop()

        if results.get("status") == "failed":
            status.update(label="❌ Search failed", state="error")
            st.error(f"Reason: {results.get('reason', results.get('error', 'Unknown failure'))}")
            st.stop()

        if "input_product" not in results:
            status.update(label="❌ Missing product data", state="error")
            st.error("Agent completed but did not return product details. Check the logs below.")
            st.stop()

        status.update(label="✅ Search complete!", state="complete")
        results_area.empty() # Clear live view to avoid duplication with final results


    # ── Store results in session state for interactivity ──────────────────
    if "last_results" not in st.session_state or st.session_state.get("last_url") != target_url:
        st.session_state["last_results"] = results
        st.session_state["last_url"] = target_url

    results = st.session_state["last_results"]
    product = results["input_product"]
    matches = results["matches"]
    
    # Merge streaming results for real-time visibility
    if "partial_matches" in st.session_state:
        for p_name, m in st.session_state["partial_matches"].items():
            if matches.get(p_name) is None:
                matches[p_name] = m
    
    st.markdown(f"### 📱 {product.get('title', 'Product')}")

    norm = product.get("normalized", {})
    col_specs = st.columns(5)
    spec_items = [
        ("Brand", norm.get("brand", "—")),
        ("Model", norm.get("model", "—")),
        ("Storage", norm.get("storage", "—")),
        ("RAM", norm.get("ram", "—")),
        ("Color", norm.get("color", "—")),
    ]
    for col, (label, val) in zip(col_specs, spec_items):
        with col:
            st.metric(label, val.upper() if val != "—" else val)

    st.markdown("---")
    st.markdown("### 🔗 Product Links Across Platforms")

    # Display platform cards with interactive "Remove" buttons
    cols = st.columns(4)
    platforms = ["amazon", "flipkart", "croma", "reliance_digital"]
    
    for i, platform in enumerate(platforms):
        with cols[i]:
            match = matches.get(platform)
            render_platform_card(platform, match)
            
            if match:
                if st.button(f"🗑️ Remove {platform.title()}", key=f"del_{platform}", use_container_width=True):
                    st.session_state["last_results"]["matches"][platform] = None
                    st.rerun()

    # ── Persistence Action ────────────────────────────────────────────────
    st.markdown("---")
    found_count = sum(1 for m in matches.values() if m)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("💾 SAVE VERIFIED DEALS TO DATABASE", use_container_width=True, type="primary"):
            from src.database.mongo_handler import MongoHandler
            db = MongoHandler()
            db.save_deal(results)
            st.success("🎉 Successfully saved to MongoDB!")
            st.balloons()

    if found_count == 4:
        st.success(f"🎉 All 4 platforms matched perfectly!")
    elif found_count > 1:
        st.info(f"✅ {found_count}/4 platforms verified.")
    else:
        st.warning("⚠️ Only one platform remaining. Save this as an exclusive deal?")


elif not search_button:
    # Landing state
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="glass-card">
            <h4>🔍 How it works</h4>
            <ol style="color:#ccc; font-size:0.9rem; line-height:2;">
                <li>Paste any mobile product URL</li>
                <li>We extract Brand, Model, Storage, RAM & Color</li>
                <li>Search the same product on all 4 platforms</li>
                <li>Return exact matching product links</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="glass-card">
            <h4>✅ Exact Match Guarantee</h4>
            <p style="color:#ccc; font-size:0.9rem; line-height:1.8;">
                We reject accessories, refurbished items, wrong variants
                (Pro vs base), and wrong storage configurations.
                Only the exact same model and variant is returned.
            </p>
        </div>
        """, unsafe_allow_html=True)
