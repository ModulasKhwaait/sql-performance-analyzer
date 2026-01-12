# SQL Performance Analyzer

A Python tool that automatically analyzes SQL Server execution plans, identifies performance issues, and provides actionable optimization recommendations.

## 🎯 Project Overview

As a SQL Server developer with 10+ years of experience, I built this tool to automate the manual process of reviewing execution plans. It can analyze single queries or batch-process hundreds of plans to identify the most critical performance issues.

## ✨ Features

- **Query Parsing & Analysis**
  - Detects common SQL anti-patterns (SELECT *, missing WHERE clauses, etc.)
  - Identifies non-SARGable predicates
  - Flags Cartesian products and improper JOINs
  - Detects repeated table access patterns

- **Execution Plan Analysis**
  - Parses SQL Server XML execution plans
  - Identifies expensive operators (scans, sorts, key lookups)
  - Extracts missing index recommendations with impact scores
  - Calculates cost percentages for each operator

- **Batch Processing**
  - Analyze multiple execution plans simultaneously
  - Rank queries by severity and cost
  - Generate comparative reports
  - Calculate health scores (0-100)

- **Actionable Recommendations**
  - Generates CREATE INDEX scripts
  - Provides specific optimization suggestions
  - Explains WHY issues impact performance
  - Prioritizes fixes by severity (Critical, High, Medium, Low)

## 🚀 Quick Start

### Setup
```bash
# Clone the repository
git clone https://github.com/YOUR-USERNAME/sql-performance-analyzer.git
cd sql-performance-analyzer

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
source venv/scripts/activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Usage

**Analyze a single query:**
```bash
# Run query smell detector
python src/analyzers/smell_detector.py

# Analyze an execution plan
python src/analyzers/plan_analyzer.py
```

**Batch analysis:**
```bash
# Analyze all plans in sample_plans directory
python src/analyzers/batch_analyzer.py
```

## 📊 Example Output
```
======================================================================
BATCH EXECUTION PLAN ANALYSIS REPORT
======================================================================

📊 Overall Statistics:
   Total Plans Analyzed: 3
   Plans with Issues: 2
   Healthy Plans: 1
   Average Health Score: 70.0/100

🚨 Issues Summary:
   Total Issues: 6
   🔴 Critical: 2
   🟠 High: 4

======================================================================
TOP 5 MOST PROBLEMATIC QUERIES
======================================================================

#1. terrible_query.xml
   Health Score: 0/100
   Issues: 3 critical, 3 high
   Cost: 125.847000
   
   🔴 [CRITICAL] TABLE_SCAN
      Query performs table scans - causes full table reads
      Recommendation: Add clustered index or covering non-clustered index

   🔴 [CRITICAL] MISSING_INDEX (98.7% impact)
      Recommendation: CREATE NONCLUSTERED INDEX IX_Orders_OrderDate
      ON dbo.Orders (OrderDate)
      INCLUDE (CustomerId, ProductId, TotalAmount)
```

## 🛠️ Technical Stack

- **Python 3.9+**
- **Libraries:**
  - `sqlparse` - SQL query parsing
  - `xml.etree.ElementTree` - Execution plan XML parsing
  - `pytest` - Testing framework

## 📁 Project Structure
```
sql-performance-analyzer/
├── src/
│   ├── parsers/
│   │   ├── query_parser.py      # SQL query parsing
│   │   └── plan_parser.py       # Execution plan XML parsing
│   ├── analyzers/
│   │   ├── smell_detector.py    # Query anti-pattern detection
│   │   ├── plan_analyzer.py     # Execution plan analysis
│   │   └── batch_analyzer.py    # Batch processing
│   ├── reporters/               # (Future: HTML report generation)
│   └── utils/
├── tests/
├── sample_plans/                # Sample execution plans
├── sample_queries/              # Sample SQL queries
├── outputs/                     # Generated reports
└── requirements.txt
```

## 🎓 Real-World Applications

1. **Production Monitoring** - Automatically review execution plans captured from production
2. **Code Review** - Validate stored procedure performance before deployment
3. **Performance Audits** - Analyze hundreds of queries to prioritize optimization work
4. **Knowledge Transfer** - Help junior DBAs learn performance tuning best practices
5. **Trend Analysis** - Track query performance degradation over time

## 🔮 Future Enhancements

- [ ] Integration with SQL Server DMVs for live monitoring
- [ ] HTML report generation with visualizations
- [ ] Historical trend tracking
- [ ] CLI tool for CI/CD integration
- [ ] Support for PostgreSQL and MySQL execution plans
- [ ] Web interface (Flask/Streamlit)

## 📝 Getting Execution Plans

From SQL Server Management Studio (SSMS):
1. Run your query with "Include Actual Execution Plan" (Ctrl+M)
2. Right-click the execution plan
3. Select "Save Execution Plan As..."
4. Save as `.sqlplan` file

Or programmatically:
```sql
SET SHOWPLAN_XML ON;
GO
-- Your query here
SELECT * FROM YourTable;
GO
SET SHOWPLAN_XML OFF;
```

## 👨‍💻 About

Built by ModulasKhwaait - SQL Server Developer with 10+ years of experience in database optimization, ETL development (SSIS), and reporting (SSRS).

This tool codifies years of hands-on performance tuning experience into an automated analysis system.

## 📄 License

MIT License - Feel free to use and modify!

---

**⭐ If you find this helpful, please star the repository!**
