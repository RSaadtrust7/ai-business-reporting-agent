import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import anthropic
import io
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Business Reporting Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }

    .stApp { background: #0a0e1a; color: #e8eaf0; }

    section[data-testid="stSidebar"] {
        background: #0d1120;
        border-right: 1px solid #1e2540;
    }

    .metric-card {
        background: linear-gradient(135deg, #111827 0%, #1a2035 100%);
        border: 1px solid #1e2d4a;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #4fc3f7; }
    .metric-label { font-size: 0.75rem; color: #7a8aa0; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
    .metric-delta-pos { font-size: 0.8rem; color: #4caf50; margin-top: 2px; }
    .metric-delta-neg { font-size: 0.8rem; color: #ef5350; margin-top: 2px; }

    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #4fc3f7;
        text-transform: uppercase; letter-spacing: 2px;
        border-bottom: 1px solid #1e2d4a; padding-bottom: 8px; margin-bottom: 16px;
    }

    .insight-box {
        background: #111827;
        border-left: 3px solid #4fc3f7;
        border-radius: 0 8px 8px 0;
        padding: 16px 20px;
        margin: 12px 0;
        font-size: 0.92rem;
        line-height: 1.6;
        color: #c8d0dc;
    }

    .stButton > button {
        background: linear-gradient(135deg, #1565c0, #0288d1);
        color: white; border: none; border-radius: 8px;
        padding: 10px 24px; font-weight: 600;
        font-family: 'Space Grotesk', sans-serif;
        transition: all 0.2s;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(79,195,247,0.3); }

    div[data-testid="stFileUploader"] {
        background: #111827; border: 2px dashed #1e2d4a;
        border-radius: 12px; padding: 10px;
    }

    .stDataFrame { border-radius: 8px; overflow: hidden; }

    h1 { color: #e8eaf0 !important; font-weight: 700 !important; }
    h2, h3 { color: #b0bec5 !important; font-weight: 600 !important; }

    .hero-title {
        font-size: 2.4rem; font-weight: 700; color: #ffffff;
        line-height: 1.2; margin-bottom: 8px;
    }
    .hero-sub { font-size: 1rem; color: #607d8b; margin-bottom: 32px; }

    .tag {
        display: inline-block; background: #1e2d4a; color: #4fc3f7;
        padding: 3px 10px; border-radius: 20px; font-size: 0.72rem;
        font-weight: 600; letter-spacing: 0.5px; margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame) -> dict:
    kpis = {}
    numeric_cols = df.select_dtypes(include='number').columns.tolist()

    if 'Revenue' in df.columns:
        kpis['total_revenue'] = df['Revenue'].sum()
        kpis['avg_monthly_revenue'] = df['Revenue'].mean()
        kpis['revenue_growth'] = ((df['Revenue'].iloc[-1] - df['Revenue'].iloc[0]) / df['Revenue'].iloc[0]) * 100

    if 'Expenses' in df.columns:
        kpis['total_expenses'] = df['Expenses'].sum()

    if 'Revenue' in df.columns and 'Expenses' in df.columns:
        df['Profit'] = df['Revenue'] - df['Expenses']
        kpis['total_profit'] = df['Profit'].sum()
        kpis['avg_margin'] = (df['Profit'] / df['Revenue']).mean() * 100

    if 'Units_Sold' in df.columns:
        kpis['total_units'] = df['Units_Sold'].sum()

    if 'New_Customers' in df.columns:
        kpis['total_new_customers'] = df['New_Customers'].sum()

    kpis['numeric_cols'] = numeric_cols
    kpis['rows'] = len(df)
    kpis['cols'] = len(df.columns)
    return kpis


def build_charts(df: pd.DataFrame) -> dict:
    """Build charts and return as bytes dict."""
    plt.style.use('dark_background')
    chart_bytes = {}
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    date_col = next((c for c in df.columns if 'month' in c.lower() or 'date' in c.lower() or 'period' in c.lower()), None)
    x_labels = df[date_col].astype(str).tolist() if date_col else [str(i) for i in range(len(df))]

    # Chart 1 — Revenue vs Expenses
    if 'Revenue' in df.columns and 'Expenses' in df.columns:
        fig, ax = plt.subplots(figsize=(10, 4))
        fig.patch.set_facecolor('#111827')
        ax.set_facecolor('#111827')
        ax.plot(x_labels, df['Revenue'], color='#4fc3f7', linewidth=2.5, marker='o', markersize=4, label='Revenue')
        ax.plot(x_labels, df['Expenses'], color='#ef5350', linewidth=2, linestyle='--', marker='s', markersize=4, label='Expenses')
        if 'Profit' not in df.columns:
            df['Profit'] = df['Revenue'] - df['Expenses']
        ax.fill_between(range(len(x_labels)), df['Revenue'], df['Expenses'],
                        where=df['Revenue'] >= df['Expenses'], alpha=0.15, color='#4caf50')
        ax.set_xticks(range(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=8, color='#7a8aa0')
        ax.tick_params(colors='#7a8aa0')
        ax.spines['bottom'].set_color('#1e2d4a')
        ax.spines['left'].set_color('#1e2d4a')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.legend(facecolor='#0d1120', edgecolor='#1e2d4a', labelcolor='#c8d0dc')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}k'))
        ax.grid(axis='y', color='#1e2d4a', linewidth=0.5)
        ax.set_title('Revenue vs Expenses', color='#e8eaf0', fontweight='bold', pad=12)
        plt.tight_layout()
        buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#111827'); buf.seek(0)
        chart_bytes['revenue_expenses'] = buf.read(); plt.close()

    # Chart 2 — Profit Margin trend
    if 'Revenue' in df.columns and 'Expenses' in df.columns:
        df['Margin'] = ((df['Revenue'] - df['Expenses']) / df['Revenue']) * 100
        fig, ax = plt.subplots(figsize=(10, 3.5))
        fig.patch.set_facecolor('#111827')
        ax.set_facecolor('#111827')
        bar_colors = ['#4caf50' if m >= 0 else '#ef5350' for m in df['Margin']]
        bars = ax.bar(x_labels, df['Margin'], color=bar_colors, alpha=0.85, edgecolor='none', width=0.6)
        ax.set_xticks(range(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=8, color='#7a8aa0')
        ax.tick_params(colors='#7a8aa0')
        ax.spines['bottom'].set_color('#1e2d4a')
        ax.spines['left'].set_color('#1e2d4a')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
        ax.grid(axis='y', color='#1e2d4a', linewidth=0.5)
        ax.set_title('Profit Margin %', color='#e8eaf0', fontweight='bold', pad=12)
        plt.tight_layout()
        buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#111827'); buf.seek(0)
        chart_bytes['margin'] = buf.read(); plt.close()

    # Chart 3 — Correlation heatmap
    if len(numeric_cols) >= 3:
        fig, ax = plt.subplots(figsize=(7, 5))
        fig.patch.set_facecolor('#111827')
        ax.set_facecolor('#111827')
        corr = df[numeric_cols].corr()
        mask = pd.DataFrame(False, index=corr.index, columns=corr.columns)
        sns.heatmap(corr, ax=ax, cmap='coolwarm', annot=True, fmt='.2f',
                    linewidths=0.5, linecolor='#0a0e1a',
                    annot_kws={'size': 8, 'color': 'white'},
                    cbar_kws={'shrink': 0.8})
        ax.tick_params(colors='#b0bec5', labelsize=8)
        ax.set_title('Metric Correlations', color='#e8eaf0', fontweight='bold', pad=12)
        plt.tight_layout()
        buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#111827'); buf.seek(0)
        chart_bytes['correlation'] = buf.read(); plt.close()

    return chart_bytes


def call_claude(df: pd.DataFrame, kpis: dict, company_name: str) -> str:
    """Call Claude API to generate executive analysis."""
    client = anthropic.Anthropic(api_key=st.session_state.api_key)

    stats = df.describe().to_string()
    kpi_str = {k: round(float(v), 2) if isinstance(v, float) else int(v) if hasattr(v, 'item') else v
               for k, v in kpis.items() if k != 'numeric_cols'}
    sample = df.head(12).to_csv(index=False)

    prompt = f"""You are a senior business analyst preparing an executive report for {company_name}.

Here is the business data:
{sample}

Key KPIs computed:
{json.dumps(kpi_str, indent=2)}

Statistical summary:
{stats}

Write a structured executive business report with these exact sections:

## Executive Summary
2-3 sentences capturing the most important finding and overall business health.

## Performance Highlights
3-4 bullet points of the strongest positive trends with specific numbers.

## Areas of Concern
2-3 bullet points identifying risks, declining metrics, or anomalies with specific numbers.

## Key Insights & Patterns
2-3 analytical observations about correlations, seasonality, or unusual patterns in the data.

## Strategic Recommendations
4-5 actionable recommendations based on the data, each with a clear rationale.

## Outlook
1-2 sentences on projected trajectory if current trends continue.

Be specific, use the actual numbers from the data, and write like a McKinsey analyst — sharp, direct, no fluff."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1800,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_pdf(analysis: str, df: pd.DataFrame, kpis: dict, chart_bytes: dict, company_name: str) -> bytes:
    """Generate a professional PDF report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)

    styles = getSampleStyleSheet()
    story = []

    # Colors
    dark_bg = colors.HexColor('#0a0e1a')
    accent = colors.HexColor('#4fc3f7')
    text_main = colors.HexColor('#1a1a2e')
    text_light = colors.HexColor('#455a64')

    title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=24,
                                  textColor=colors.HexColor('#1a237e'), spaceAfter=4,
                                  alignment=TA_LEFT)
    subtitle_style = ParagraphStyle('Sub', fontName='Helvetica', fontSize=11,
                                     textColor=text_light, spaceAfter=2)
    section_style = ParagraphStyle('Section', fontName='Helvetica-Bold', fontSize=13,
                                    textColor=colors.HexColor('#1565c0'), spaceBefore=14, spaceAfter=6,
                                    borderPad=4)
    body_style = ParagraphStyle('Body', fontName='Helvetica', fontSize=10,
                                 textColor=text_main, leading=15, spaceAfter=6)
    bullet_style = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=10,
                                   textColor=text_main, leading=15, leftIndent=16, spaceAfter=4)

    # Header
    story.append(Paragraph(f"Business Performance Report", title_style))
    story.append(Paragraph(f"{company_name}  ·  Generated {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1565c0'), spaceAfter=16))

    # KPI summary table
    kpi_data = [['Metric', 'Value']]
    if 'total_revenue' in kpis:
        kpi_data.append(['Total Revenue', f"${kpis['total_revenue']:,.0f}"])
    if 'total_expenses' in kpis:
        kpi_data.append(['Total Expenses', f"${kpis['total_expenses']:,.0f}"])
    if 'total_profit' in kpis:
        kpi_data.append(['Total Profit', f"${kpis['total_profit']:,.0f}"])
    if 'avg_margin' in kpis:
        kpi_data.append(['Avg Profit Margin', f"{kpis['avg_margin']:.1f}%"])
    if 'revenue_growth' in kpis:
        kpi_data.append(['Revenue Growth', f"{kpis['revenue_growth']:.1f}%"])
    if 'total_new_customers' in kpis:
        kpi_data.append(['New Customers', f"{int(kpis['total_new_customers']):,}"])

    if len(kpi_data) > 1:
        t = Table(kpi_data, colWidths=[8*cm, 8*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f5f7ff'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cfd8dc')),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(t)
        story.append(Spacer(1, 16))

    # Charts
    for key, img_bytes in chart_bytes.items():
        img_buf = io.BytesIO(img_bytes)
        img = RLImage(img_buf, width=16*cm, height=6*cm)
        story.append(img)
        story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cfd8dc'), spaceAfter=12))

    # Analysis text
    for line in analysis.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], section_style))
        elif line.startswith('- ') or line.startswith('• '):
            story.append(Paragraph(f"• {line[2:]}", bullet_style))
        else:
            story.append(Paragraph(line, body_style))

    # Footer note
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cfd8dc')))
    story.append(Paragraph("Generated by AI Business Reporting Agent · Powered by Claude AI",
                            ParagraphStyle('Footer', fontName='Helvetica', fontSize=8,
                                           textColor=text_light, alignment=TA_CENTER, spaceBefore=6)))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">⚙ Configuration</div>', unsafe_allow_html=True)

    api_key = st.text_input("Anthropic API Key", type="password",
                             placeholder="sk-ant-...",
                             help="Your Anthropic API key")
    if api_key:
        st.session_state.api_key = api_key

    st.markdown("---")
    company_name = st.text_input("Company / Client Name", value="Acme Corp")
    st.markdown("---")
    st.markdown('<div class="section-header">📁 Data</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload CSV", type=['csv'])

    use_sample = st.checkbox("Use sample data", value=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem; color:#455a64; line-height:1.6;'>
    <b style='color:#4fc3f7'>Supported columns:</b><br>
    Revenue, Expenses, Units_Sold,<br>New_Customers, Churn_Rate,<br>
    Marketing_Spend, etc.<br><br>
    Any numeric CSV works.
    </div>
    """, unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-title">AI Business Reporting Agent</div>
<div class="hero-sub">Upload your business data → Get an AI-powered executive report in seconds</div>
<span class="tag">Claude AI</span>
<span class="tag">Python</span>
<span class="tag">PDF Export</span>
<span class="tag">Trend Analysis</span>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Load data
df = None
if uploaded:
    df = pd.read_csv(uploaded)
    st.success(f"✅ Loaded: {uploaded.name} ({len(df)} rows, {len(df.columns)} columns)")
elif use_sample:
    df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_data.csv'))
    st.info("📋 Using sample data — upload your own CSV in the sidebar")

if df is not None:
    kpis = compute_kpis(df)

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    cards = []
    if 'total_revenue' in kpis:
        cards.append(('Total Revenue', f"${kpis['total_revenue']/1000:.0f}k",
                       f"↑ {kpis.get('revenue_growth', 0):.1f}% growth", True))
    if 'total_profit' in kpis:
        cards.append(('Total Profit', f"${kpis['total_profit']/1000:.0f}k", '', True))
    if 'avg_margin' in kpis:
        cards.append(('Avg Margin', f"{kpis['avg_margin']:.1f}%", '', True))
    if 'total_new_customers' in kpis:
        cards.append(('New Customers', f"{int(kpis['total_new_customers']):,}", '', True))

    for i, col in enumerate([col1, col2, col3, col4]):
        if i < len(cards):
            label, val, delta, pos = cards[i]
            delta_html = f'<div class="metric-delta-{"pos" if pos else "neg"}">{delta}</div>' if delta else ''
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
                {delta_html}
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Data preview + charts
    tab1, tab2, tab3 = st.tabs(["📊 Charts", "🗂 Data Preview", "🤖 AI Analysis"])

    with tab1:
        chart_bytes = build_charts(df.copy())
        if 'revenue_expenses' in chart_bytes:
            st.image(chart_bytes['revenue_expenses'], use_container_width=True)
        c1, c2 = st.columns(2)
        if 'margin' in chart_bytes:
            c1.image(chart_bytes['margin'], use_container_width=True)
        if 'correlation' in chart_bytes:
            c2.image(chart_bytes['correlation'], use_container_width=True)

    with tab2:
        st.dataframe(df.style.background_gradient(cmap='Blues', subset=df.select_dtypes('number').columns),
                     use_container_width=True)
        st.caption(f"{kpis['rows']} rows · {kpis['cols']} columns")

    with tab3:
        if 'api_key' not in st.session_state or not st.session_state.api_key:
            st.warning("⚠️ Enter your Anthropic API key in the sidebar to generate AI analysis.")
        else:
            if st.button("🚀 Generate Executive Report", use_container_width=True):
                with st.spinner("Analyzing data with Claude AI..."):
                    analysis = call_claude(df, kpis, company_name)
                    st.session_state.analysis = analysis
                    st.session_state.chart_bytes = build_charts(df.copy())

            if 'analysis' in st.session_state:
                st.markdown('<div class="section-header">Executive Analysis</div>', unsafe_allow_html=True)
                for line in st.session_state.analysis.split('\n'):
                    line = line.strip()
                    if line.startswith('## '):
                        st.markdown(f"### {line[3:]}")
                    elif line.startswith('- ') or line.startswith('• '):
                        st.markdown(f'<div class="insight-box">• {line[2:]}</div>', unsafe_allow_html=True)
                    elif line:
                        st.write(line)

                st.markdown("<br>", unsafe_allow_html=True)
                pdf_bytes = generate_pdf(
                    st.session_state.analysis, df, kpis,
                    st.session_state.chart_bytes, company_name
                )
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"{company_name.replace(' ', '_')}_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

else:
    st.markdown("""
    <div style='text-align:center; padding: 80px 0; color: #455a64;'>
        <div style='font-size:3rem;'>📂</div>
        <div style='font-size:1.1rem; margin-top:12px;'>Upload a CSV or enable sample data in the sidebar</div>
        <div style='font-size:0.85rem; margin-top:8px; color:#37474f;'>Supports any business data: sales, finance, operations, marketing</div>
    </div>
    """, unsafe_allow_html=True)
