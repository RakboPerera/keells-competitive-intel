"""
Facebook Ad Campaign Intelligence
===================================
Shows active Facebook ad campaigns from the Meta Ad Library.
Claude AI analyzes and compares campaigns across brands.
Data is refreshed daily via GitHub Actions.

Run: streamlit run intel_dashboard.py
"""

import json, os
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import requests

# =============================================================================
# CONFIG
# =============================================================================

BRANDS = {
    "Keells Super": {"color": "#E82AAE", "icon": "🔴", "type": "benchmark",
                      "page_id": "108836225822670"},
    "Cargills Food City": {"color": "#26EA9F", "icon": "🟢", "type": "competitor",
                            "page_id": "155866468723"},
    "Softlogic Glomark": {"color": "#6366f1", "icon": "🟣", "type": "competitor",
                           "page_id": "354233975342508"},
    "SPAR Sri Lanka": {"color": "#f59e0b", "icon": "🟡", "type": "competitor",
                        "page_id": "290159608091322"},
}

DATA_DIR = Path("data")

# =============================================================================
# PAGE SETUP
# =============================================================================

st.set_page_config(page_title="FB Ad Intel — Keells", page_icon="📊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
    .stApp { font-family: 'DM Sans', sans-serif; }
    .agent-response {
        background: linear-gradient(135deg, rgba(232,42,174,0.06), rgba(38,234,159,0.06));
        border: 1px solid rgba(232,42,174,0.15); border-radius: 12px;
        padding: 24px; margin: 16px 0; line-height: 1.7;
    }
    .ad-card {
        padding: 14px; border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px; margin: 8px 0; font-size: 14px;
        background: rgba(255,255,255,0.02);
    }
    .ad-meta {
        display: flex; justify-content: space-between;
        margin-bottom: 8px; color: #888; font-size: 12px;
    }
    .validation-pass { color: #26EA9F; }
    .validation-warn { color: #f59e0b; }
    .validation-fail { color: #ff4444; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# HELPERS
# =============================================================================

def get_claude_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("ANTHROPIC_API_KEY", "")


def save_data(data, filename):
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def load_data(filename):
    fp = DATA_DIR / filename
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def ad_library_url(page_id):
    return (f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
            f"&country=LK&is_targeted_country=false&media_type=all&search_type=page"
            f"&sort_data[direction]=desc&sort_data[mode]=total_impressions"
            f"&view_all_page_id={page_id}")


# =============================================================================
# VALIDATION
# =============================================================================

def validate_scraped_data(ad_data):
    """Validate scraped data quality and return report."""
    report = {}
    for brand, info in ad_data.items():
        ads = info.get("ads", [])
        total = len(ads)
        with_date = sum(1 for a in ads if a.get("start_date"))
        with_text = sum(1 for a in ads if a.get("text_preview"))
        with_platforms = sum(1 for a in ads if a.get("platforms"))
        with_snapshot = sum(1 for a in ads if a.get("ad_snapshot_url"))
        with_id = sum(1 for a in ads if a.get("id") and not a["id"].startswith("ad_"))

        # Quality score 0-100
        if total == 0:
            score = 0
        else:
            score = int((
                (with_date / total) * 25 +
                (with_text / total) * 25 +
                (with_platforms / total) * 20 +
                (with_snapshot / total) * 15 +
                (with_id / total) * 15
            ))

        report[brand] = {
            "total": total,
            "with_date": with_date,
            "with_text": with_text,
            "with_platforms": with_platforms,
            "with_snapshot": with_snapshot,
            "with_real_id": with_id,
            "quality_score": score,
            "collected_at": info.get("collected_at", "?"),
        }
    return report


# =============================================================================
# CLAUDE AI
# =============================================================================

def call_claude(system, user, api_key):
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                      "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 4000,
                  "system": system, "messages": [{"role": "user", "content": user}]},
            timeout=120,
        )
        data = resp.json()
        if "content" in data:
            return data["content"][0]["text"]
        st.error(f"Claude error: {data.get('error', {}).get('message', 'Unknown')}")
    except Exception as e:
        st.error(f"Claude API failed: {e}")
    return None


def summarize_ads(ads, name):
    if not ads:
        return f"{name}: No active ads found."
    lines = [f"{name} ({len(ads)} active Facebook ads):"]
    for a in ads[:25]:
        start = a.get("start_date") or "?"
        plats = a.get("platforms") or []
        plats_str = ", ".join(plats) if isinstance(plats, list) else str(plats)
        text = a.get("text_preview", "")
        text_str = f' — "{text[:120]}"' if text else ""
        status = a.get("status", "active")
        lines.append(f"  [{start}] ({status}) {plats_str}{text_str}")
    return "\n".join(lines)


def ai_individual_campaigns(all_brand_ads, api_key):
    all_txt = "\n\n".join(summarize_ads(ads, name) for name, ads in all_brand_ads.items())
    return call_claude(
        "You are a senior retail marketing analyst specializing in the Sri Lankan supermarket industry. "
        "Analyze each brand's currently active Facebook ad campaigns from the Meta Ad Library. "
        "Be specific, cite actual ad content where visible. Use markdown.",
        f"""Analyze each supermarket brand's currently active Facebook ad campaigns.

{all_txt}

For EACH brand, provide:

## Keells Super — Campaign Review
- **Campaign volume:** How many active ads? Is this high/low for a supermarket?
- **Key themes:** Dominant messages (promotions, loyalty, freshness, delivery, seasonal, brand building)
- **Content strategy:** What type of ads? Platform focus?
- **Standout campaigns:** Which ads seem to be flagship or high-effort?
- **Digital maturity rating:** 1-5 with justification

## Cargills Food City — Campaign Review
(Same structure)

## Softlogic Glomark — Campaign Review
(Same structure)

## SPAR Sri Lanka — Campaign Review
(Same structure)

Be detailed. Reference actual ad content where available.""",
        api_key,
    )


def ai_strategic_comparison(keells_ads, competitor_ads, api_key):
    keells_txt = summarize_ads(keells_ads, "Keells Super")
    comp_txt = "\n\n".join(summarize_ads(ads, name) for name, ads in competitor_ads.items())
    return call_claude(
        "You are a senior strategy consultant presenting to John Keells Holdings leadership. "
        "Compare Keells Super's active Facebook ad campaigns against competitors. "
        "Be direct, insightful, actionable. Use markdown.",
        f"""Strategic comparison of currently active Facebook ad campaigns.

KEELLS SUPER (our brand):
{keells_txt}

COMPETITORS:
{comp_txt}

Provide:

## Competitive Landscape Overview
Who is dominating Facebook advertising? Share of voice comparison.

## Head-to-Head: Keells vs Cargills Food City
Direct comparison — where each wins, key battleground.

## Head-to-Head: Keells vs Softlogic Glomark
Premium segment rivalry.

## Head-to-Head: Keells vs SPAR Sri Lanka
International vs local branding.

## SWOT Analysis — Keells Facebook Advertising
- **Strengths:** What Keells is doing well
- **Weaknesses:** Where Keells falls short
- **Opportunities:** Gaps competitors leave open
- **Threats:** Competitor moves that should concern Keells

## Strategic Recommendations
Top 5 prioritized actions with expected impact and urgency (High/Medium/Low) for each.""",
        api_key,
    )


# =============================================================================
# APP
# =============================================================================

def main():
    claude_key = get_claude_key()

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown("### 🏪 Competitors")
        selected = st.multiselect("Select", ["Cargills Food City", "Softlogic Glomark", "SPAR Sri Lanka"],
                                   default=["Cargills Food City", "Softlogic Glomark", "SPAR Sri Lanka"])

        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.caption(
            "This tool shows **currently active Facebook ad campaigns** "
            "from the Meta Ad Library for Keells and competitors. "
            "Data is refreshed automatically every day."
        )

    # ── HEADER ──
    st.markdown("""
    <div style="margin-bottom:20px">
        <span style="font-size:11px;letter-spacing:3px;text-transform:uppercase;
              background:linear-gradient(90deg,#E82AAE,#26EA9F);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              font-weight:700">Octave Intelligence</span>
        <h1 style="margin:4px 0 0;font-size:30px">Facebook Ad Campaign Intelligence</h1>
        <p style="color:#888;margin:0">Currently active Facebook ads — Keells Super vs Competitors</p>
    </div>
    """, unsafe_allow_html=True)

    # ── STATUS BAR ──
    cached_data = load_data("ad_library_data.json")
    if cached_data:
        total_cached = sum(len(v.get("ads", [])) for v in cached_data.values())
        ts = next((v["collected_at"] for v in cached_data.values() if v.get("collected_at")), "?")
        try:
            ts_display = datetime.fromisoformat(ts).strftime("%d %b %Y, %I:%M %p")
        except Exception:
            ts_display = ts[:16]

        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:12px 16px;border-radius:10px;background:rgba(38,234,159,0.06);
                    border:1px solid rgba(38,234,159,0.15);margin-bottom:16px">
            <div>
                <span style="color:#26EA9F;font-weight:600">{total_cached} active Facebook ads</span>
                <span style="color:#888;margin-left:12px">Last scraped: {ts_display}</span>
                <span style="color:#555;margin-left:8px;font-size:12px">(auto-updates daily)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        links_btn = st.button("🔗 Open Meta Ad Library", use_container_width=True)
    else:
        st.warning("No ad data found. Data will appear once the daily scraper runs.")
        links_btn = st.button("🔗 Open Meta Ad Library", use_container_width=True)

    if links_btn:
        for name in ["Keells Super"] + selected:
            pid = BRANDS[name]["page_id"]
            st.markdown(f"{BRANDS[name]['icon']} **[{name} — View on Ad Library]({ad_library_url(pid)})**")

    st.markdown("---")

    # Load data
    ad_data = load_data("ad_library_data.json") or {}

    # ── TABS ──
    tab1, tab2, tab3 = st.tabs([
        "📣 Active Facebook Campaigns",
        "🤖 AI Campaign Analysis",
        "✅ Data Validation",
    ])

    # ════════════════════════════════════════════════
    # TAB 1 — ACTIVE CAMPAIGNS
    # ════════════════════════════════════════════════
    with tab1:
        st.markdown("#### Currently Active Facebook Ads")
        st.caption("From the Meta Ad Library. Shows all ads currently running on Facebook. Updated daily.")

        if not ad_data:
            st.info("No ad data yet. Data auto-updates daily via the scheduled scraper.")
            st.markdown("---")
            st.markdown("#### 🔗 Browse Ad Library directly")
            cols = st.columns(min(len(selected) + 1, 4))
            for i, name in enumerate(["Keells Super"] + selected):
                with cols[i % len(cols)]:
                    pid = BRANDS[name]["page_id"]
                    st.link_button(f"{BRANDS[name]['icon']} {name}", ad_library_url(pid), use_container_width=True)
        else:
            overview_brands = ["Keells Super"] + [b for b in selected if b in ad_data]

            # Metrics
            cols = st.columns(len(overview_brands))
            for i, brand in enumerate(overview_brands):
                ads = ad_data.get(brand, {}).get("ads", [])
                active = [a for a in ads if a.get("status", "active") == "active"]
                with cols[i]:
                    st.markdown(f"**{BRANDS[brand]['icon']} {brand}**")
                    st.metric("Active Ads", len(active))
                    plats = {}
                    for ad in active:
                        for p in (ad.get("platforms") or []):
                            plats[p] = plats.get(p, 0) + 1
                    if plats:
                        st.caption(" · ".join(f"{p}: {c}" for p, c in sorted(plats.items(), key=lambda x: -x[1])))

            st.markdown("---")

            # Per-brand ad lists
            for brand in overview_brands:
                ads = ad_data.get(brand, {}).get("ads", [])
                active = [a for a in ads if a.get("status", "active") == "active"]

                with st.expander(f"{BRANDS[brand]['icon']} {brand} — {len(active)} active ads", expanded=(brand == "Keells Super")):
                    if not active:
                        pid = BRANDS[brand]["page_id"]
                        st.caption(f"No ads found. [Check Ad Library]({ad_library_url(pid)})")
                        continue
                    for ad in active[:30]:
                        dt = ad.get("start_date") or "?"
                        plats = ad.get("platforms") or []
                        plats_str = ", ".join(plats) if isinstance(plats, list) else str(plats)
                        snapshot = ad.get("ad_snapshot_url", "")
                        has_real = ad.get("has_real_id", False)
                        if not has_real or not snapshot or "ad_" in ad.get("id", ""):
                            snapshot = ""
                        text = ad.get("text_preview", "")

                        # Fallback link to brand's Ad Library page
                        pid = BRANDS.get(brand, {}).get("page_id", "")
                        fallback_link = ad_library_url(pid) if pid else ""

                        link_html = ""
                        if snapshot:
                            link_html = f'<a href="{snapshot}" target="_blank" style="font-size:12px;color:#E82AAE">View ad on Ad Library →</a>'
                        elif fallback_link:
                            link_html = f'<a href="{fallback_link}" target="_blank" style="font-size:12px;color:#888">View all {brand} ads →</a>'

                        st.markdown(f"""<div class="ad-card">
                            <div class="ad-meta"><span>📅 Started: {dt}</span><span>📱 {plats_str or 'Facebook'}</span></div>
                            {f'<div style="font-size:13px;margin-top:4px;color:#ccc">{text[:280]}</div>' if text else '<div style="font-size:13px;color:#666">No ad copy extracted</div>'}
                            <div style="margin-top:6px">{link_html}</div>
                        </div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 🔗 View full Ad Library")
            cols = st.columns(min(len(selected) + 1, 4))
            for i, name in enumerate(["Keells Super"] + selected):
                with cols[i % len(cols)]:
                    pid = BRANDS[name]["page_id"]
                    st.link_button(f"{BRANDS[name]['icon']} {name}", ad_library_url(pid), use_container_width=True)

    # ════════════════════════════════════════════════
    # TAB 2 — AI ANALYSIS
    # ════════════════════════════════════════════════
    with tab2:
        if not claude_key:
            st.warning("Claude API key not configured. Add to `.streamlit/secrets.toml`.")
        elif not ad_data:
            st.info("No ad data yet. Data auto-updates daily.")
        else:
            # Summary table
            rows = []
            for brand in ["Keells Super"] + [b for b in selected if b in ad_data]:
                ads = ad_data.get(brand, {}).get("ads", [])
                active = [a for a in ads if a.get("status", "active") == "active"]
                plats = {}
                for ad in active:
                    for p in (ad.get("platforms") or []):
                        plats[p] = plats.get(p, 0) + 1
                rows.append({
                    "Brand": f"{BRANDS[brand]['icon']} {brand}",
                    "Active Facebook Ads": len(active),
                    "On Facebook": plats.get("Facebook", 0),
                    "On Instagram": plats.get("Instagram", 0),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown("---")

            # Part 1
            st.markdown("### 📋 Part 1 — Campaign Breakdown by Brand")
            st.caption("What is each supermarket currently running on Facebook?")

            if st.button("🤖 Analyze Each Brand's Campaigns", key="p1", use_container_width=True, type="primary"):
                all_brand_ads = {}
                for brand in ["Keells Super"] + [b for b in selected if b in ad_data]:
                    ads = ad_data.get(brand, {}).get("ads", [])
                    all_brand_ads[brand] = [a for a in ads if a.get("status", "active") == "active"]

                with st.spinner("Claude is analyzing each brand's Facebook campaigns..."):
                    result = ai_individual_campaigns(all_brand_ads, claude_key)
                if result:
                    save_data({"analysis": result, "at": datetime.now().isoformat()}, "individual_analysis.json")
                    st.markdown('<div class="agent-response">', unsafe_allow_html=True)
                    st.markdown(result)
                    st.markdown('</div>', unsafe_allow_html=True)

            cached_ind = load_data("individual_analysis.json")
            if cached_ind:
                with st.expander("📄 Previous brand analysis", expanded=False):
                    st.caption(f"Generated: {cached_ind.get('at', '')[:16]}")
                    st.markdown(cached_ind.get("analysis", ""))

            st.markdown("---")

            # Part 2
            st.markdown("### ⚔️ Part 2 — Strategic Comparison")
            st.caption("Head-to-head comparison + SWOT + recommendations for Keells")

            if st.button("🤖 Run Strategic Comparison", key="p2", use_container_width=True, type="primary"):
                keells = [a for a in ad_data.get("Keells Super", {}).get("ads", [])
                          if a.get("status", "active") == "active"]
                comps = {}
                for n in selected:
                    if n in ad_data:
                        comps[n] = [a for a in ad_data[n].get("ads", [])
                                    if a.get("status", "active") == "active"]

                with st.spinner("Claude is running strategic comparison..."):
                    result = ai_strategic_comparison(keells, comps, claude_key)
                if result:
                    save_data({"analysis": result, "at": datetime.now().isoformat()}, "strategic_analysis.json")
                    st.markdown('<div class="agent-response">', unsafe_allow_html=True)
                    st.markdown(result)
                    st.markdown('</div>', unsafe_allow_html=True)

            cached_strat = load_data("strategic_analysis.json")
            if cached_strat:
                with st.expander("📄 Previous strategic analysis", expanded=False):
                    st.caption(f"Generated: {cached_strat.get('at', '')[:16]}")
                    st.markdown(cached_strat.get("analysis", ""))

    # ════════════════════════════════════════════════
    # TAB 3 — DATA VALIDATION
    # ════════════════════════════════════════════════
    with tab3:
        st.markdown("#### Data Quality Validation")
        st.caption("Checks the quality and completeness of the Facebook ad data.")

        if not ad_data:
            st.info("No data to validate yet. Data auto-updates daily.")
        else:
            validation = validate_scraped_data(ad_data)

            for brand, v in validation.items():
                config = BRANDS.get(brand, {})
                score = v["quality_score"]
                score_color = "validation-pass" if score >= 60 else "validation-warn" if score >= 30 else "validation-fail"

                st.markdown(f"""
                **{config.get('icon', '')} {brand}** — 
                <span class="{score_color}">Quality: {score}/100</span>
                """, unsafe_allow_html=True)

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total Ads", v["total"])
                c2.metric("With Date", f"{v['with_date']}/{v['total']}")
                c3.metric("With Ad Copy", f"{v['with_text']}/{v['total']}")
                c4.metric("With Platforms", f"{v['with_platforms']}/{v['total']}")
                c5.metric("With Ad Link", f"{v['with_snapshot']}/{v['total']}")

                if score < 30 and v["total"] > 0:
                    pid = BRANDS[brand]["page_id"]
                    st.warning(f"Low quality data. [Verify on Ad Library]({ad_library_url(pid)})")
                elif v["total"] == 0:
                    pid = BRANDS[brand]["page_id"]
                    st.error(f"No ads found. [Check Ad Library manually]({ad_library_url(pid)})")

                st.markdown("---")

            # Raw data view
            with st.expander("🔍 View raw data", expanded=False):
                for brand in ad_data:
                    ads = ad_data[brand].get("ads", [])
                    if ads:
                        st.markdown(f"**{brand}** — {len(ads)} ads")
                        df = pd.DataFrame(ads)
                        show_cols = [c for c in ["id", "start_date", "platforms", "text_preview", "status"]
                                     if c in df.columns]
                        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

    # Footer
    st.markdown("---")
    st.caption("Facebook Ad Campaign Intelligence · Octave / John Keells Holdings PLC · "
               "Source: Meta Ad Library · AI: Claude")


if __name__ == "__main__":
    main()
