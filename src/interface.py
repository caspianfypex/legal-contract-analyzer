import tempfile
import datetime
import streamlit as st
import main
from streamlit.runtime.uploaded_file_manager import UploadedFile


def create_temp_file_path(file: UploadedFile):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(file.read())
        return tmp.name


st.set_page_config(
    page_title="Legal Risk Intelligence System",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ──────────────────────────────────────────────────────────────────────────
# GLOBAL STYLE — "Government / Chancery" luxury theme
# Deep navy + parchment ink + brushed-gold accents, serif typography,
# engraved borders, seal-like badges.
# ──────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Libre+Baskerville:wght@400;700&display=swap');

:root {
    --navy-900: #0c1420;
    --navy-800: #121c2b;
    --navy-700: #1a2536;
    --navy-600: #212e42;
    --gold-500: #9a3f41;
    --gold-400: #b5585a;
    --gold-300: #cfcabb;
    --ink-100: #e9e6dd;
    --ink-200: #d3cfc3;
    --ink-muted: #8b93a0;
    --border-hair: #2c3a4d;
    --crimson: #b5585a;
}

/* ---------- Base canvas ---------- */
.stApp {
    background: var(--navy-900);
    color: var(--ink-200);
    font-family: 'EB Garamond', Georgia, serif;
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* ---------- Typography ---------- */
h1, h2, h3, h4 {
    font-family: 'Libre Baskerville', Georgia, serif !important;
    color: var(--ink-100) !important;
    letter-spacing: 0.2px;
    font-weight: 700 !important;
}

h1 {
    font-size: 1.9rem !important;
    border-bottom: 2px solid var(--ink-100);
    padding-bottom: 0.6rem;
    margin-bottom: 0.3rem !important;
}

p, span, label, div, li {
    font-family: 'EB Garamond', Georgia, serif;
}

/* Small caps eyebrow labels */
.eyebrow {
    font-family: 'EB Garamond', serif;
    font-size: 0.75rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--ink-muted);
    margin-bottom: 0.25rem;
}

/* ---------- Header banner ---------- */
.header-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.1rem 1.6rem;
    background: var(--navy-800);
    border: 1px solid var(--border-hair);
    border-radius: 2px;
    margin-bottom: 1.6rem;
}

.header-banner .seal {
    font-size: 2rem;
}

.header-meta {
    text-align: right;
    font-family: 'EB Garamond', serif;
    font-size: 0.75rem;
    letter-spacing: 1px;
    color: var(--ink-muted);
    text-transform: uppercase;
}

.header-meta .classification {
    color: var(--crimson);
    font-weight: 700;
    border: 1px solid var(--crimson);
    padding: 2px 10px;
    border-radius: 2px;
    display: inline-block;
    margin-top: 4px;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: var(--navy-700);
    border-right: 1px solid var(--border-hair);
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.6rem;
}
section[data-testid="stSidebar"] h2, 
section[data-testid="stSidebar"] h3 {
    font-size: 1.05rem !important;
    color: var(--ink-100) !important;
}

/* ---------- Dividers ---------- */
hr, .stDivider {
    border-color: var(--border-hair) !important;
}

/* Section divider */
.ornate-divider {
    display: flex;
    align-items: center;
    text-align: center;
    color: var(--ink-muted);
    margin: 1.2rem 0;
    font-size: 0.75rem;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.ornate-divider::before, .ornate-divider::after {
    content: "";
    flex: 1;
    border-bottom: 1px solid var(--border-hair);
}
.ornate-divider span { padding: 0 1rem; }

/* ---------- Buttons ---------- */
.stButton>button {
    background: var(--navy-600);
    color: var(--ink-100);
    border-radius: 2px;
    border: 1px solid var(--gold-500);
    padding: 0.65rem 1.2rem;
    font-family: 'EB Garamond', serif;
    font-weight: 600;
    letter-spacing: 0.5px;
    font-size: 0.9rem;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    background: var(--navy-700);
    color: var(--ink-100);
    border-color: var(--gold-400);
}

/* Download button */
.stDownloadButton>button {
    background: var(--navy-600);
    border: 1px solid var(--gold-500);
    color: var(--ink-100);
    font-family: 'EB Garamond', serif;
    letter-spacing: 0.5px;
    font-size: 0.9rem;
    border-radius: 2px;
}
.stDownloadButton>button:hover {
    background: var(--navy-700);
    color: var(--ink-100);
    border-color: var(--gold-400);
}

/* ---------- Inputs ---------- */
.stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
    background-color: var(--navy-800) !important;
    color: var(--ink-100) !important;
    border: 1px solid var(--border-hair) !important;
    border-radius: 2px !important;
    font-family: 'EB Garamond', Georgia, serif !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--ink-100) !important;
    box-shadow: none !important;
}

/* ---------- File uploader ---------- */
[data-testid="stFileUploader"] {
    border: 1px dashed var(--border-hair);
    padding: 1.2rem;
    border-radius: 2px;
    background-color: var(--navy-800);
}
[data-testid="stFileUploaderDropzone"] {
    background-color: transparent !important;
}

/* ---------- Metric cards ---------- */
[data-testid="stMetric"] {
    background: var(--navy-800);
    border: 1px solid var(--border-hair);
    border-top: 2px solid var(--ink-100);
    padding: 1.1rem;
    border-radius: 2px;
}
[data-testid="stMetricLabel"] {
    font-family: 'EB Garamond', serif !important;
    letter-spacing: 1px;
    font-size: 0.75rem !important;
    color: var(--ink-muted) !important;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    color: var(--ink-100) !important;
    font-family: 'Libre Baskerville', serif !important;
    font-size: 1.8rem !important;
}

/* ---------- Expander (risk cards) ---------- */
.streamlit-expanderHeader {
    font-family: 'EB Garamond', serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px;
    color: var(--ink-100) !important;
    background-color: var(--navy-700) !important;
    border: 1px solid var(--border-hair) !important;
    border-radius: 2px !important;
}
.streamlit-expanderContent {
    background-color: var(--navy-800) !important;
    border: 1px solid var(--border-hair) !important;
    border-top: none !important;
}

/* Risk card interior */
.risk-card {
    padding: 1.2rem 1.4rem;
    background-color: var(--navy-800);
    border-radius: 2px;
    border-left: 3px solid var(--ink-100);
    line-height: 1.65;
}
.risk-card .field-label {
    font-family: 'EB Garamond', serif;
    font-size: 0.75rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--ink-muted);
    display: block;
    margin-top: 0.9rem;
    margin-bottom: 0.2rem;
}
.risk-card .field-label:first-child { margin-top: 0; }
.risk-card .source-line {
    margin-top: 1rem;
    padding-top: 0.7rem;
    border-top: 1px dotted var(--border-hair);
    font-size: 0.85rem;
    color: var(--ink-muted);
    font-style: italic;
}

/* Severity badges */
.badge {
    display: inline-block;
    font-family: 'EB Garamond', serif;
    font-size: 0.72rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 2px;
    margin-right: 8px;
}
.badge-critical { background: transparent; color: var(--crimson); border: 1px solid var(--crimson); }
.badge-high { background: transparent; color: #8a5a1f; border: 1px solid #8a5a1f; }
.badge-medium { background: transparent; color: #6b6459; border: 1px solid var(--border-hair); }
.badge-low { background: transparent; color: #3f6b48; border: 1px solid #3f6b48; }

/* Info / warning / success / error boxes — force dark backgrounds */
.stAlert, div[data-testid="stAlert"] {
    border-radius: 2px !important;
    border-left: 3px solid var(--gold-500) !important;
    background-color: var(--navy-600) !important;
    font-family: 'EB Garamond', serif !important;
}
.stAlert *, div[data-testid="stAlert"] * {
    color: var(--ink-100) !important;
    background-color: transparent !important;
}
.stAlert svg, div[data-testid="stAlert"] svg {
    fill: var(--gold-400) !important;
}

/* Footer */
.footer-note {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-hair);
    text-align: center;
    font-family: 'EB Garamond', serif;
    font-size: 0.75rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--ink-muted);
}

</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────
today = datetime.datetime.now().strftime("%d %B %Y")

st.markdown(f"""
<div class="header-banner">
    <div style="display:flex; align-items:center; gap:1rem;">
        <div class="seal">⚖️</div>
        <div>
            <div class="eyebrow">Office of Legal Risk Intelligence</div>
            <h1 style="margin:0; border:none; padding:0;">Legal Risk Intelligence Dashboard</h1>
        </div>
    </div>
    <div class="header-meta">
        Ref. No. LRI-{today.replace(" ", "-").upper()}<br>
        <span class="classification">Attorney Work Product</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<p style="font-size:1.05rem; color:var(--ink-200); max-width:820px;">
Submit a contract for structured clause extraction, calibrated risk scoring, and
detection of legal vulnerabilities, in accordance with standard due-diligence protocol.
</p>
""", unsafe_allow_html=True)

st.markdown('<div class="ornate-divider"><span>Analysis Request</span></div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# SIDEBAR — Analysis Engine Configuration
# ──────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="eyebrow">Configuration</div>', unsafe_allow_html=True)
    st.header("⚙️ Analysis Engine")

    search_mode = st.selectbox(
        "Risk Analysis Depth",
        [
            "Low — Efficient Legal Analysis",
            "Medium — Standard Legal Review",
            "High — Deep Legal Reasoning",
            "Ultra — Court-Grade Audit"
        ]
    )

    st.markdown('<div class="ornate-divider"><span>Document Intake</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="eyebrow">Document Intake</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "📄 Upload Contract (PDF only)",
        type=["pdf"],
        accept_multiple_files=False,
        help="Only one PDF contract may be uploaded per analysis."
    )

    if uploaded_file is not None:
        st.success(f"Received: {uploaded_file.name}")

    st.warning("Only PDF contracts are accepted. Scanned images may reduce accuracy.")

    st.markdown('<div class="ornate-divider"><span>Guidance</span></div>', unsafe_allow_html=True)

    st.info("""
**Analysis Levels**

• **Low** — Quick risk detection  
• **Medium** — Balanced legal scan  
• **High** — Deep clause interpretation  
• **Ultra** — Multi-pass contradiction & liability analysis
""")

    st.markdown(
        '<div class="footer-note" style="margin-top:2rem;">Confidential &nbsp;·&nbsp; For Internal Review Only</div>',
        unsafe_allow_html=True
    )


# ──────────────────────────────────────────────────────────────────────────
# MAIN — Context & Execution
# ──────────────────────────────────────────────────────────────────────────
colA, colB = st.columns([2, 1])

with colA:
    st.markdown('<div class="eyebrow">Supplementary Information</div>', unsafe_allow_html=True)
    st.subheader("🧾 Legal Context (Optional)")
    context_query = st.text_area(
        "Provide contract context to improve accuracy",
        placeholder="Example: SaaS agreement between EU company and US vendor with GDPR obligations...",
        height=120
    )

with colB:
    st.markdown('<div class="eyebrow">Proceed</div>', unsafe_allow_html=True)
    st.subheader("🚀 Execution")
    analyze = st.button("Run Full Legal Risk Analysis", use_container_width=True)

st.markdown('<div class="ornate-divider"><span>Execution</span></div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# RESULTS
# ──────────────────────────────────────────────────────────────────────────
if analyze:

    if not uploaded_file:
        st.error("⚠️ Please upload a PDF contract first.")
        st.stop()

    temp_path = create_temp_file_path(uploaded_file)

    with st.spinner("Analyzing contract with legal AI engine..."):
        result = main.run_pipeline(
            docspath=temp_path,
            context_query=context_query,
            mode=search_mode
        )[1]

    st.success("Analysis Completed Successfully")

    # Summary metrics strip
    severities = [r.severity for r in result.risks]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Findings", len(result.risks))
    m2.metric("Critical", severities.count("Critical"))
    m3.metric("High", severities.count("High"))
    m4.metric("Medium / Low", severities.count("Medium") + severities.count("Low"))

    st.markdown('<div class="ornate-divider"><span>Findings</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="eyebrow">Register of Detected Legal Risks</div>', unsafe_allow_html=True)
    st.subheader("⚠️ Detected Legal Risks")

    badge_map = {
        "Critical": ("🔴", "badge-critical"),
        "High": ("🟠", "badge-high"),
        "Medium": ("🟡", "badge-medium"),
        "Low": ("🟢", "badge-low"),
    }

    for i, r in enumerate(result.risks, start=1):
        emoji, badge_class = badge_map.get(r.severity, ("⚪", "badge-medium"))

        with st.expander(f"{emoji}  Finding {i:02d} — {r.severity} — {r.risk_title}"):
            card_html = f"""<div class="risk-card">
<span class="badge {badge_class}">{r.severity} Risk</span>
<span class="field-label">Why It Is Risky</span>
{r.why_it_is_risky}
<span class="field-label">Possible Consequences</span>
{r.possible_consequences}
<div class="source-line">Source: {r.section}{f', Clause {r.clause}' if r.clause else ''} — Page {r.page}</div>
</div>"""
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown('<div class="ornate-divider"><span>Report</span></div>', unsafe_allow_html=True)

    st.download_button(
        "⬇️ Export Legal Risk Report",
        data=str(result),
        file_name="legal_risk_report.txt",
        mime="text/plain",
        use_container_width=True
    )

    st.markdown(
        f'<div class="footer-note">Generated {today} &nbsp;·&nbsp; Legal Risk Intelligence System &nbsp;·&nbsp; Not Legal Advice</div>',
        unsafe_allow_html=True
    )