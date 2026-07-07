# StackCheck: DP Data Validation Automation Platform

StackCheck is an enterprise-grade standalone application built for Data Processing (DP) teams in market research. It automates the validation of stacked datasets (SPSS `.sav`, Excel `.xlsx`/`.xls`, `.csv`) against client-delivered DP Specification Sheets before delivery to analysts.

StackCheck runs **completely offline** with no external AI API requirements, ensuring absolute privacy, speed, and reliability.

---

## Key Features

1. **SPSS Metadata Validation**: Scans variable labels coverage, checks for empty or inconsistent value labels, and identifies missing user value declarations.
2. **Dataset Structure Profiling**: Instantly computes row/column summaries, datatype variables distribution, and automatically infers key brand variable and respondent ID candidates.
3. **Intelligent Binary Validator**: Detects non 0/1 binary codings (like `1/2`, `2/4`, `Y/N`, `Yes/No`, `True/False`, `T/F`) and grades discrepancies as PASS, WARNING, or FAIL with confidence ratings.
4. **Auto-Fix Recommendations**: Recommends mapping rules (e.g. `1 -> 0; 2 -> 1` or `Yes -> 1; No -> 0`) to resolve coding variances.
5. **Refined Quality Scoring**: Deducts scores based on Core vs. Optional missing variables, duplicates, and warnings to prevent overly harsh rejections.
6. **Flexible Project Profiles**: Save tracker rules templates (like Beverage, Chocolate, or Automotive trackers) by uploading reference DP specification sheets.
7. **Document Reporting**: Outputs professional styled multi-sheet Excel workbooks and ReportLab PDF reports complete with cover summaries.

---

## Technical Stack

- **Backend**: FastAPI (Python 3.12), SQLite (via SQLAlchemy), Pyreadstat, Pandas, OpenPyXL, ReportLab.
- **Frontend**: React 19, TypeScript, Vite, TailwindCSS, Recharts, Zustand.
- **Desktop**: Electron.
- **Deployment**: Docker, Docker Compose.

---

## Installation & Running

For installation steps, refer to [INSTALL.md](file:///Users/chethan/Desktop/StackCheck/INSTALL.md).

### Quick Start Web (Development)

1. **Start FastAPI Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start Vite React Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

### Quick Start Desktop (Electron)

Ensure Node modules are installed in both frontend and desktop directories, build the frontend, and boot Electron:
```bash
# Build Frontend
cd frontend
npm run build

# Start Electron shell
cd ../desktop
npm install
npm start
```
