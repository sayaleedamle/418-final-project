"""TruthCheck Streamlit app.

Calls the TruthCheck Flask API and renders a colour-coded fact-check report.
Set the API_URL environment variable to point at the deployed API.
"""

from __future__ import annotations

import json
import os
import time

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8080")

_VERDICT_EMOJI = {
    "consensus_supported":    "✅",
    "consensus_contradicted": "❌",
    "contested":              "⚠️",
    "unverifiable":           "❓",
    "out_of_scope":           "⬜",
}

_VERDICT_LABEL = {
    "consensus_supported":    "Supported by consensus",
    "consensus_contradicted": "Contradicted by consensus",
    "contested":              "Contested / Debated",
    "unverifiable":           "Unverifiable",
    "out_of_scope":           "Out of scope",
}

# Colours that match Streamlit's default palette reasonably well
_VERDICT_BG = {
    "consensus_supported":    "#d4edda",
    "consensus_contradicted": "#f8d7da",
    "contested":              "#fff3cd",
    "unverifiable":           "#e2e3e5",
    "out_of_scope":           "#f8f9fa",
}

_CHART_COLORS = {
    "Supported by consensus":    "#2ecc71",
    "Contradicted by consensus": "#e74c3c",
    "Contested / Debated":       "#f39c12",
    "Unverifiable":              "#95a5a6",
    "Out of scope":              "#bdc3c7",
}


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TruthCheck",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🔬 TruthCheck")
    st.caption("Health & Nutrition Fact-Checker for YouTube")
    st.divider()

    api_url = st.text_input(
        "API URL",
        value=API_URL,
        help="Base URL of the TruthCheck API service.",
    )

    max_claims = st.slider(
        "Max claims to evaluate",
        min_value=1,
        max_value=20,
        value=10,
        help="Fewer claims = faster results. Use 3–5 for quick demos.",
    )

    st.divider()
    st.markdown("""
**Verdict key**
| | |
|---|---|
| ✅ | Supported by consensus |
| ❌ | Contradicted by consensus |
| ⚠️ | Contested / actively debated |
| ❓ | Unverifiable |
| ⬜ | Out of scope |
""")

    st.divider()
    st.caption("Evidence sourced from PubMed, Cochrane Reviews, CDC, WHO & NIH.")


# ── Header ────────────────────────────────────────────────────────────────────

st.title("🔬 TruthCheck")
st.subheader("AI-powered health & nutrition fact-checker for YouTube videos")
st.markdown(
    "Paste a YouTube URL below. TruthCheck extracts every health claim from the "
    "transcript and evaluates each one against peer-reviewed scientific literature."
)
st.divider()


# ── Input ─────────────────────────────────────────────────────────────────────

col_input, col_btn = st.columns([5, 1])
with col_input:
    video_url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed",
    )
with col_btn:
    analyze = st.button("Analyze ▶", type="primary", use_container_width=True)

with st.expander("📋 Paste transcript manually (use this if URL fetch fails)"):
    pasted_transcript = st.text_area(
        "Transcript text",
        placeholder="Paste the video transcript here...",
        height=150,
        label_visibility="collapsed",
    )

if not analyze or not video_url.strip():
    st.info(
        "Enter a health or nutrition YouTube video URL and click **Analyze ▶**. "
        "Processing takes 1–3 minutes depending on transcript length."
    )
    st.stop()

# Try fetching transcript locally first (works locally, blocked on Cloud Run)
transcript_to_send: str | None = pasted_transcript.strip() if pasted_transcript.strip() else None
if not transcript_to_send:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
        import re as _re
        _id_match = _re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", video_url)
        if _id_match:
            _api = YouTubeTranscriptApi()
            _vid = _id_match.group(1)
            try:
                _t = _api.list(_vid).find_manually_created_transcript(["en"])
            except Exception:
                _t = _api.list(_vid).find_generated_transcript(["en"])
            transcript_to_send = " ".join(s.text.strip() for s in _t.fetch() if s.text.strip())
    except Exception:
        pass  # Cloud Run blocks YouTube — API will try itself or fail gracefully


# ── API call ──────────────────────────────────────────────────────────────────

with st.spinner("Fetching transcript and evaluating claims — please wait…"):
    t0 = time.monotonic()
    try:
        payload: dict = {"video": video_url.strip(), "max_claims": max_claims}
        if transcript_to_send:
            payload["transcript"] = transcript_to_send
        resp = requests.post(
            f"{api_url.rstrip('/')}/check",
            json=payload,
            timeout=360,
        )
    except requests.ConnectionError:
        st.error(
            f"Could not connect to the API at **{api_url}**. "
            "Is the API service running?"
        )
        st.stop()
    except requests.Timeout:
        st.error("The request timed out after 6 minutes.")
        st.stop()
    elapsed = time.monotonic() - t0

# ── Error handling ────────────────────────────────────────────────────────────

if resp.status_code == 422:
    st.error(f"Transcript unavailable: {resp.json().get('error', 'Unknown error')}")
    st.stop()
elif resp.status_code == 400:
    st.error(f"Bad request: {resp.json().get('error', 'Unknown error')}")
    st.stop()
elif resp.status_code == 503:
    st.error("API is not configured — GEMINI_API_KEY is missing on the server.")
    st.stop()
elif not resp.ok:
    st.error(f"API error {resp.status_code}: {resp.json().get('error', resp.text)}")
    st.stop()

data    = resp.json()
summary = data.get("summary", {})
claims  = data.get("claims", [])


# ── Summary metrics ───────────────────────────────────────────────────────────

st.success(
    f"Analysis complete — **{data['total_claims']} claims** evaluated in {elapsed:.0f}s"
)
st.markdown(f"**Video:** [{data['video_url']}]({data['video_url']})")
st.divider()

m1, m2, m3, m4 = st.columns(4)
m1.metric("✅ Supported",    summary.get("supported", 0))
m2.metric("❌ Contradicted", summary.get("contradicted", 0))
m3.metric("⚠️ Contested",    summary.get("misleading", 0))
m4.metric("❓ Unverifiable", summary.get("unverifiable", 0))


# ── Verdict distribution chart ────────────────────────────────────────────────

if claims:
    verdict_counts: dict[str, int] = {}
    for c in claims:
        label = _VERDICT_LABEL.get(c["verdict"], c["verdict"])
        verdict_counts[label] = verdict_counts.get(label, 0) + 1

    chart_df = (
        pd.DataFrame(list(verdict_counts.items()), columns=["Verdict", "Count"])
        .sort_values("Count", ascending=False)
    )
    st.bar_chart(chart_df.set_index("Verdict"))


# ── Claim cards ───────────────────────────────────────────────────────────────

st.divider()
st.subheader(f"Claim-by-claim breakdown ({len(claims)})")

for i, claim in enumerate(claims, 1):
    verdict = claim.get("verdict", "unverifiable")
    emoji   = _VERDICT_EMOJI.get(verdict, "❓")
    label   = _VERDICT_LABEL.get(verdict, verdict)
    ts      = claim.get("timestamp_s")
    ts_str  = f" · ~{int(ts)}s" if ts is not None else ""
    title   = claim.get("claim", "")
    preview = title[:90] + "…" if len(title) > 90 else title

    with st.expander(f"{i}. {emoji} **{label}**{ts_str} — {preview}"):

        # ── Claim & context ───────────────────────────────────────────────
        st.markdown(f"**Claim:** {title}")
        if claim.get("context"):
            st.caption(f"📍 Context: *{claim['context']}*")

        st.divider()

        # ── Verdict & explanation ─────────────────────────────────────────
        st.markdown(f"**Verdict:** {emoji} `{verdict}`")
        st.markdown(f"**Explanation:** {claim.get('explanation', '')}")

        # ── Citations ─────────────────────────────────────────────────────
        citations = claim.get("citations", [])
        eq = claim.get("evidence_query", "")
        if citations:
            st.divider()
            st.markdown(f"**Evidence ({len(citations)} source{'s' if len(citations) > 1 else ''}):**")
            if eq:
                st.caption(f"🔍 PubMed query: `{eq}`")
            for j, cit in enumerate(citations, 1):
                url     = cit.get("url", "")
                src     = cit.get("source", "Source")
                excerpt = cit.get("excerpt", "").strip()

                col_label, col_link = st.columns([3, 1])
                with col_label:
                    st.markdown(f"**{j}. {src}**")
                with col_link:
                    if url:
                        st.markdown(f"[Open ↗]({url})")

                if excerpt:
                    st.markdown(
                        f"<blockquote style='border-left:3px solid #aaa;"
                        f"padding:6px 12px;color:#555;font-size:0.88em'>"
                        f"{excerpt}</blockquote>",
                        unsafe_allow_html=True,
                    )
        else:
            eq = claim.get("evidence_query", "")
            st.caption(
                "⚠️ No citations retrieved from PubMed / Cochrane / CDC / WHO / NIH "
                f"for this claim — verdict is based on model knowledge only."
                + (f"\n\n🔍 Search query used: `{eq}`" if eq else "")
            )


# ── Download ──────────────────────────────────────────────────────────────────

st.divider()
dl_col1, dl_col2 = st.columns(2)

with dl_col1:
    st.download_button(
        "⬇️ Download JSON report",
        data=json.dumps(data, indent=2),
        file_name=f"truthcheck_{data['video_id']}.json",
        mime="application/json",
        use_container_width=True,
    )

with dl_col2:
    # Build a simple Markdown report for the second download
    md_lines = [
        f"# TruthCheck Report\n",
        f"**Video:** {data['video_url']}  ",
        f"**Claims:** {data['total_claims']} · "
        f"Supported: {summary.get('supported',0)} · "
        f"Contradicted: {summary.get('contradicted',0)} · "
        f"Contested: {summary.get('misleading',0)} · "
        f"Unverifiable: {summary.get('unverifiable',0)}\n",
        "---\n",
    ]
    for i, c in enumerate(claims, 1):
        v     = c.get("verdict", "unverifiable")
        emoji = _VERDICT_EMOJI.get(v, "❓")
        ts    = c.get("timestamp_s")
        ts_s  = f" (~{int(ts)}s)" if ts is not None else ""
        md_lines += [
            f"## {i}. {emoji} `{v}`{ts_s}",
            f"> {c.get('claim','')}",
            f"\n{c.get('explanation','')}",
        ]
        for cit in c.get("citations", []):
            url = cit.get("url")
            src = cit.get("source", "")
            md_lines.append(f"- [{src}]({url})" if url else f"- {src}")
        md_lines.append("\n---\n")

    st.download_button(
        "⬇️ Download Markdown report",
        data="\n".join(md_lines),
        file_name=f"truthcheck_{data['video_id']}.md",
        mime="text/markdown",
        use_container_width=True,
    )
