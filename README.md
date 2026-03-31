# AI Business Reporting Agent

> Transform raw business CSV data into executive-grade PDF reports using Claude AI — in seconds.

---

## What It Does

Upload any business CSV (sales, finance, operations) and the agent automatically:

- Computes KPIs — revenue, profit margins, growth rates, customer metrics
- Generates 3 charts — revenue/expense trends, profit margin bars, correlation heatmap
- Calls **Claude AI** to write a structured executive analysis (6 sections: summary, highlights, risks, insights, recommendations, outlook)
- Exports a professional **PDF report** ready to share with stakeholders

## Demo

![App Screenshot](https://raw.githubusercontent.com/placeholder/screenshot.png)

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| AI Analysis | Anthropic Claude API |
| Data Processing | Pandas |
| Charts | Matplotlib, Seaborn |
| PDF Generation | ReportLab |

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-username/ai-business-reporting-agent.git
cd ai-business-reporting-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key
cp .env.example .env
# Edit .env and add your Anthropic API key

# 4. Run
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Usage

1. Enter your **Anthropic API key** in the sidebar (or set `ANTHROPIC_API_KEY` in `.env`)
2. Upload your CSV **or** use the included sample data
3. Browse the **Charts** and **Data Preview** tabs
4. Go to **AI Analysis** → click **Generate Executive Report**
5. Download the PDF

### Supported CSV columns
`Revenue`, `Expenses`, `Units_Sold`, `New_Customers`, `Churn_Rate`, `Marketing_Spend` — any numeric CSV works.

---

## Sample Data

`sample_data.csv` contains 12 months of synthetic business metrics (Jan–Dec 2024):
Revenue, Expenses, Units Sold, New Customers, Churn Rate, Marketing Spend, Support Tickets.

---

## Use Cases

- Weekly/monthly executive reporting for ops managers and CFOs
- Client-facing business performance summaries
- Automating 3–5 hours/week of manual reporting work

---

Built by **Saadallah Elbejjaj** · AI Automation & Agentic AI Consultant
