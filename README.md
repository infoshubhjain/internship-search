# Summer 2027 SWE Internship Tracker

🚀 **Automated, comprehensive internship tracking system for UIUC F-1 international students**

## 🎯 What This Does

- **479 verified internship opportunities** across 5 priority levels
- **Automated daily updates** via GitHub Actions
- **Multi-source aggregation** from top GitHub repositories (vanshb03, ApplyGuy, SimplifyJobs)
- **Application tracking** with status management and analytics
- **Priority-based sorting** for efficient application strategy

## 📁 Files

### Core Tracking
- `Summer2027_SWE_Tracker.csv` - **MAIN FILE** - Comprehensive tracker with 479 internships
- `SWE_Internship_Master_Tracker.csv` - Original 60+ target companies
- `scraped_internships.csv` - Raw data from GitHub repos

### Automation Scripts
- `update_all.py` - Master script to update all data (run this locally)
- `scrape_github_repos.py` - Scrapes internship data from GitHub repos
- `merge_internship_data.py` - Merges data and assigns priorities
- `scrape_job_boards.py` - Job board scraper (Indeed, BuiltIn)

### Configuration
- `.github/workflows/update-internships.yml` - GitHub Actions for daily automation
- `requirements.txt` - Python dependencies

### Documentation
- `RECOMMENDATIONS.md` - Detailed strategy guide and enhancement ideas
- `README.md` - This file
- `Search_Queries.csv` - Job board search URLs
- `Weekly_Plan.csv` - Daily tasks and reminders
- `ai_automation_prompt.txt` - AI agent automation prompt

## 🚀 Quick Start

### 1. Use the Comprehensive Tracker
Open `Summer2027_SWE_Tracker.csv` - this is your main working file with all 479 opportunities.

### 2. Priority-Based Application Strategy
- **Priority 1 (30 entries)**: Underclassman programs - APPLY FIRST
- **Priority 2 (20 entries)**: Banks/fintech - HIGH CPT SPONSORSHIP  
- **Priority 3 (42 entries)**: F500 companies - GOOD VOLUME
- **Priority 4 (34 entries)**: Big Tech/unicorns - COMPETITIVE
- **Priority 5 (353 entries)**: Startups/other - FILLER OPPORTUNITIES

### 3. Daily Application Routine
**Target**: 5-10 applications per day (don't skip weekends)
**Focus**: Priority 1 → Priority 2 → Priority 3
**Tracking**: Update Status column immediately after applying

Status workflow:
- `Not Applied` → `Applied` → `Interviewing` → `Offer`/`Rejected`
- Fill in: Date Applied, Interview Date, Offer Status, Follow-up Date

## 🤖 Automation

### GitHub Actions (Automatic)
Your repository is set up with automatic daily updates at 6 AM UTC:
- Scrapes GitHub repos for new internships
- Updates your tracker automatically
- Commits changes to GitHub

**Manual trigger**: Go to GitHub Actions tab → "Update Internship Tracker" → "Run workflow"

### Local Updates
Run the master script to update data locally:
```bash
python3 update_all.py
```

This will:
1. Scrape GitHub repos for new data
2. Merge with existing tracker
3. Update priorities and sponsorship info
4. Save updated CSV files

## 📊 Data Sources

The system aggregates data from:
- **vanshb03/Summer2027-Internships** - Community-maintained list
- **ApplyGuy/2027-Internships** - JSON API with verified listings
- **SimplifyJobs/Summer2027-Internships** - Pitt CSC & Simplify curated list
- **Original master tracker** - 60+ target companies

## 🎓 Priority System

1. **Underclassman programs** - Google STEP, Microsoft Explore, Meta University, Amazon SDE, Capital One, Uber, Pinterest, Lyft
2. **Banks/fintech** - JPMorgan, Goldman Sachs, Morgan Stanley, Bank of America, Citi, Visa, Mastercard, etc.
3. **F500 non-tech** - Walmart, Target, GM, Ford, John Deere, etc.
4. **Big Tech/unicorns** - Apple, Netflix, Airbnb, Stripe, etc.
5. **Startups/other** - All other opportunities

## 🔧 Setup

### Initial Setup
```bash
# Clone the repository
git clone https://github.com/infoshubhjain/internship-search.git
cd internship-search

# Install dependencies
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run initial update
python3 update_all.py
```

### GitHub Actions Setup
The workflow is already configured. Just push to GitHub:
```bash
git add .
git commit -m "Set up internship tracking automation"
git push
```

## 📈 Enhancement Ideas

See `RECOMMENDATIONS.md` for detailed ideas including:
- Email notifications for high-priority roles
- Deadline tracking and alerts
- Application analytics dashboard
- Calendar integration
- Notion/Airtable sync
- Company research automation
- Network mapping with UIUC alumni

## 🎯 Key Reminders

- Apply to 5-10 internships daily (don't skip weekends)
- CPT eligibility is critical - check work authorization notes
- Banks typically sponsor CPT
- Keep tracker updated with status (Applied, Interview, Offer, Rejected)
- Priority 1 roles have limited application windows
- Use automation to save time on data collection
- Focus on high-probability opportunities first

## 📊 Current Stats

- **Total opportunities**: 479
- **Priority 1**: 30 (underclassman programs)
- **Priority 2**: 20 (banks/fintech)
- **Priority 3**: 42 (F500 companies)
- **Priority 4**: 34 (big tech/unicorns)
- **Priority 5**: 353 (startups/other)
- **Data sources**: 4 major GitHub repositories
- **Update frequency**: Daily (automatic)

## 🏆 Success Metrics

Track your progress:
- Applications per week (target: 35-50)
- Interview rate (target: 10-15%)
- Offer rate (target: 2-5%)
- Response time by priority
- Best sources for interviews

## 🤝 Contributing

Feel free to:
- Add new data sources to the scrapers
- Improve priority assignment logic
- Enhance sponsorship detection
- Add new automation features
- Share your success stories!

## 📞 Support

For detailed strategy recommendations and technical enhancement ideas, see `RECOMMENDATIONS.md`.

---

**Built for UIUC F-1 international students seeking Summer 2027 SWE internships** 🎓