import { useState, useEffect } from "react";
import { useAppStore } from "../store/useAppStore";
import { FileSpreadsheet, FileText, ShieldCheck, AlertTriangle, Search, CheckCircle2, X } from "lucide-react";

export default function ValidationCenter() {
  const { activeReport, setActiveReport } = useAppStore();
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [varSearch, setVarSearch] = useState<string>("");
  const [varFilter, setVarFilter] = useState<string>("ALL"); // ALL, PASSED, MISSING_CORE, MISSING_OPTIONAL, UNEXPECTED

  // Auto-Fix states
  const [selectedFixes, setSelectedFixes] = useState<string[]>([]);
  const [fixing, setFixing] = useState<boolean>(false);
  const [fixResult, setFixResult] = useState<any | null>(null);

  // Initialize selected fixes on report load
  useEffect(() => {
    if (activeReport && activeReport.binary_validation) {
      const initialSelected = activeReport.binary_validation.issues
        .filter((issue: any) => issue.severity === "WARNING" && issue.suggested_fix)
        .map((issue: any) => issue.variable);
      setSelectedFixes(initialSelected);
      setFixResult(null);
    } else {
      setSelectedFixes([]);
      setFixResult(null);
    }
  }, [activeReport]);

  // Auto-Fix helper functions
  const checkableIssues = activeReport?.binary_validation?.issues?.filter(
    (issue: any) => issue.severity === "WARNING" && issue.suggested_fix
  ) || [];
  
  const allChecked = checkableIssues.length > 0 && checkableIssues.every(
    (issue: any) => selectedFixes.includes(issue.variable)
  );

  const toggleAll = () => {
    if (allChecked) {
      const checkableNames = checkableIssues.map((issue: any) => issue.variable);
      setSelectedFixes(selectedFixes.filter(v => !checkableNames.includes(v)));
    } else {
      const checkableNames = checkableIssues.map((issue: any) => issue.variable);
      setSelectedFixes([...new Set([...selectedFixes, ...checkableNames])]);
    }
  };

  const toggleFix = (variable: string) => {
    if (selectedFixes.includes(variable)) {
      setSelectedFixes(selectedFixes.filter(v => v !== variable));
    } else {
      setSelectedFixes([...selectedFixes, variable]);
    }
  };

  const handleApproveFixes = async () => {
    if (selectedFixes.length === 0 || !activeReport || !activeReport.id) return;
    setFixing(true);
    setFixResult(null);
    try {
      const res = await fetch("/api/v1/auto-fix", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_id: activeReport.id,
          variables: selectedFixes
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Auto-fix compilation failed.");
      }
      const data = await res.json();
      setFixResult(data);
      
      // Auto trigger file download
      const downloadLink = document.createElement("a");
      downloadLink.href = data.download_url;
      downloadLink.setAttribute("download", data.corrected_file);
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
    } catch (err: any) {
      alert("Failed to apply auto-fixes: " + err.message);
    } finally {
      setFixing(false);
    }
  };

  if (!activeReport) {
    return (
      <div className="bg-neutral-950 border border-neutral-900 p-16 rounded-2xl text-center space-y-5 animate-apple-fade max-w-md mx-auto mt-12">
        <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto stroke-[1.5]" />
        <div className="space-y-2">
          <h2 className="text-md font-medium text-white">No Active Report</h2>
          <p className="text-xs text-neutral-500 leading-relaxed max-w-xs mx-auto">
            Please run a new quality check in the Ingestion Hub or select a past validation wave from the Audit Trail logs.
          </p>
        </div>
      </div>
    );
  }

  const {
    metadata,
    profiling,
    metadata_validation,
    master_validation,
    binary_validation,
    completeness_validation,
    null_analysis,
    duplicate_analysis,
    empty_variables,
    datatype_validation,
    quality_score,
    final_status,
    report_xlsx_url,
    report_pdf_url
  } = activeReport;

  const completenessData = completeness_validation || {
    status: "INFO",
    total_respondents: metadata?.rows || 0,
    total_analysis_variables: 0,
    fully_missing_respondents_count: 0,
    fully_missing_respondents_pct: 0,
    coverage_distribution: [],
    fully_missing_respondents: []
  };

  const tabs = [
    { id: "overview", label: "Executive Overview" },
    { id: "variables", label: `Variables (${master_validation.issues.length})` },
    { id: "metadata", label: `SPSS Metadata (${metadata_validation.issues.length})` },
    { id: "binary", label: `Binary Fixes (${binary_validation.issues.length})` },
    { id: "completeness", label: `Completeness (${completenessData.fully_missing_respondents_count})` },
    { id: "null_types", label: "Nulls & Datatypes" },
    { id: "duplicates", label: "Duplicates" }
  ];

  // SVG Activity Ring parameters
  const score = quality_score.score;
  const radius = 35;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Dynamic Ring and Badge colors following Apple System styling
  let ringColor = "#30d158"; // Green
  let textColorClass = "text-emerald-400";
  if (score < 60) {
    ringColor = "#ff453a"; // Red
    textColorClass = "text-rose-500";
  } else if (score < 80) {
    ringColor = "#ff9f0a"; // Amber/Orange
    textColorClass = "text-amber-450";
  } else if (score < 95) {
    ringColor = "#0071e3"; // Apple Blue
    textColorClass = "text-blue-400";
  }

  // Variables list filtering logic
  const filteredVariables = master_validation.issues.filter((issue: any) => {
    // Search filter
    const matchesSearch = issue.variable.toLowerCase().includes(varSearch.toLowerCase());
    if (!matchesSearch) return false;

    // Category status filter
    if (varFilter === "ALL") return true;
    if (varFilter === "PASSED" && issue.status === "FOUND") return true;
    if (varFilter === "UNEXPECTED" && issue.status === "UNEXPECTED") return true;
    if (varFilter === "MISSING_CORE" && issue.status === "MISSING" && issue.required) return true;
    if (varFilter === "MISSING_OPTIONAL" && issue.status === "MISSING" && !issue.required) return true;
    return false;
  });

  const topNullVariables = [...(null_analysis?.variables || [])]
    .sort((a: any, b: any) => (b.null_pct || 0) - (a.null_pct || 0))
    .slice(0, 10);

  return (
    <div className="space-y-8 animate-apple-fade">
      
      {/* File Info Header bar */}
      <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden">
        <div className="space-y-1.5 min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-white tracking-tight truncate max-w-lg">{metadata.filename}</h1>
            <span className={final_status === "PASS" ? "badge-apple-pass" : final_status === "WARNING" ? "badge-apple-warn" : "badge-apple-fail"}>
              {final_status}
            </span>
          </div>
          <p className="text-xs text-neutral-500 font-mono">
            Size: {metadata.file_size_mb.toFixed(2)} MB | Columns: {metadata.columns} | Records: {metadata.rows.toLocaleString()}
          </p>
        </div>

        {/* Quality Activity Ring & Exports */}
        <div className="flex items-center gap-6 shrink-0">
          
          {/* Apple Watch style Activity Ring */}
          <div className="flex items-center gap-3">
            <div className="relative h-20 w-20 flex items-center justify-center shrink-0">
              <svg className="h-full w-full transform -rotate-90" viewBox="0 0 80 80">
                {/* Background Ring */}
                <circle
                  cx="40"
                  cy="40"
                  r={radius}
                  stroke="var(--svg-ring-bg)"
                  strokeWidth="6"
                  fill="transparent"
                />
                {/* Active Score Ring */}
                <circle
                  cx="40"
                  cy="40"
                  r={radius}
                  stroke={ringColor}
                  strokeWidth="6"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute flex flex-col items-center justify-center">
                <span className="text-xl font-bold text-white tracking-tighter leading-none">{score}</span>
                <span className="text-[8px] text-neutral-500 font-semibold tracking-wider uppercase mt-0.5">Index</span>
              </div>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Quality Score</p>
              <h4 className={`text-sm font-semibold tracking-tight ${textColorClass} mt-0.5`}>{quality_score.status}</h4>
            </div>
          </div>

          <div className="h-10 w-px bg-neutral-900"></div>

          {/* Downloads & Reset */}
          <div className="flex items-center gap-2">
            {report_xlsx_url && (
              <a
                href={report_xlsx_url}
                className="apple-btn-secondary py-2 px-3.5 text-xs text-emerald-600 dark:text-emerald-400 bg-emerald-500/5 dark:bg-emerald-500/10 border-emerald-500/15 dark:border-emerald-500/25 hover:bg-emerald-500/15 dark:hover:bg-emerald-500/20 hover:border-emerald-500/30 dark:hover:border-emerald-500/40 hover:text-emerald-500 dark:hover:text-emerald-300 font-medium rounded-full shadow-sm transition-all"
                title="Download Excel Spreadsheet"
              >
                <FileSpreadsheet className="h-4 w-4 text-emerald-500 dark:text-emerald-450" />
                <span className="hidden sm:inline">Excel Report</span>
              </a>
            )}
            {report_pdf_url && (
              <a
                href={report_pdf_url}
                className="apple-btn-secondary py-2 px-3.5 text-xs text-rose-600 dark:text-rose-450 bg-rose-500/5 dark:bg-rose-500/10 border-rose-500/15 dark:border-rose-500/25 hover:bg-rose-500/15 dark:hover:bg-rose-500/20 hover:border-rose-500/30 dark:hover:border-rose-500/40 hover:text-rose-500 dark:hover:text-rose-350 font-medium rounded-full shadow-sm transition-all"
                title="Download PDF Report"
              >
                <FileText className="h-4 w-4 text-rose-500 dark:text-rose-450" />
                <span className="hidden sm:inline">PDF Report</span>
              </a>
            )}
            <button
              onClick={() => setActiveReport(null)}
              className="apple-btn-secondary py-2 px-3.5 text-xs text-neutral-600 dark:text-neutral-400 bg-neutral-500/5 dark:bg-neutral-500/10 border-neutral-500/15 dark:border-neutral-500/25 hover:bg-rose-500/10 dark:hover:bg-rose-500/20 hover:border-rose-500/30 dark:hover:border-rose-500/45 hover:text-rose-500 dark:hover:text-rose-400 font-medium rounded-full shadow-sm transition-all flex items-center gap-1.5 cursor-pointer group"
              title="Close and Clear Current Report View"
            >
              <X className="h-4 w-4 text-neutral-500 dark:text-neutral-400 group-hover:text-rose-500 dark:group-hover:text-rose-400 transition-colors" />
              <span className="hidden sm:inline">Clear Report</span>
            </button>
          </div>
        </div>
      </div>

      {/* iOS/macOS-style Segmented Sliding Tab Control */}
      <div className="bg-neutral-950 p-1.5 rounded-xl flex gap-1 overflow-x-auto border border-neutral-900">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-xs font-medium rounded-lg whitespace-nowrap transition-all duration-150 ${
              activeTab === tab.id
                ? "bg-neutral-900 text-white font-semibold shadow-sm apple-tab-active"
                : "text-neutral-550 hover:text-neutral-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="space-y-6">
        
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="grid gap-6 md:grid-cols-3">
            {/* Profiling metadata summary card */}
            <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Dataset Profile</h3>
              <div className="space-y-3 font-medium text-xs">
                <div className="flex justify-between py-2 border-b border-neutral-900">
                  <span className="text-neutral-500">Numeric Columns</span>
                  <span className="text-white font-semibold">{profiling.numeric_count}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-neutral-900">
                  <span className="text-neutral-500">String Columns</span>
                  <span className="text-white font-semibold">{profiling.string_count}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-neutral-900">
                  <span className="text-neutral-500">Binary Flags</span>
                  <span className="text-white font-semibold">{profiling.binary_count}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-neutral-900">
                  <span className="text-neutral-500">Respondent Key</span>
                  <span className="font-mono text-white font-semibold">{profiling.potential_respondent_id || "None"}</span>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-neutral-500">Brand Dimension</span>
                  <span className="font-mono text-white font-semibold">{profiling.potential_brand_variable || "None"}</span>
                </div>
                <div className="flex justify-between py-2 border-t border-neutral-900 mt-1 pt-3">
                  <span className="text-neutral-500">Fully Missing Respondents</span>
                  <span className="text-white font-semibold">
                    {completenessData.fully_missing_respondents_count} ({completenessData.fully_missing_respondents_pct}%)
                  </span>
                </div>
              </div>
            </div>

            {/* Score penalties details card */}
            <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl md:col-span-2 space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Deduction Wave Logs</h3>
              <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
                {quality_score.penalties.map((p: any, idx: number) => (
                  <div key={idx} className="flex justify-between items-center text-xs p-3.5 bg-neutral-900/30 rounded-xl border border-neutral-900">
                    <span className="text-neutral-300 font-medium">{p.description}</span>
                    <span className="text-rose-500 font-semibold font-mono">-{p.value} pts</span>
                  </div>
                ))}
                {quality_score.penalties.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-14 text-neutral-500">
                    <CheckCircle2 className="h-8 w-8 text-emerald-450 mb-2 stroke-[1.5]" />
                    <p className="text-xs font-medium text-neutral-450">Perfect validation run. No deductions applied.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Variables checklist Tab */}
        {activeTab === "variables" && (
          <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-6">
            
            {/* Search and Category Filters */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-neutral-900 pb-5">
              <div className="relative w-full md:max-w-xs">
                <Search className="h-4 w-4 text-neutral-600 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter by variable name..."
                  value={varSearch}
                  onChange={(e) => setVarSearch(e.target.value)}
                  className="apple-input w-full pl-9 py-2 text-xs"
                />
              </div>
              
              {/* Category Segment Filter buttons */}
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: "ALL", label: "All variables" },
                  { id: "PASSED", label: "Passed" },
                  { id: "MISSING_CORE", label: "Missing Core (-10)" },
                  { id: "MISSING_OPTIONAL", label: "Missing Opt (-2)" },
                  { id: "UNEXPECTED", label: "Unexpected" }
                ].map(opt => (
                  <button
                    key={opt.id}
                    onClick={() => setVarFilter(opt.id)}
                    className={`px-3 py-1.5 rounded-lg text-[10px] font-medium border transition-all duration-200 ${
                      varFilter === opt.id
                        ? "bg-neutral-200 dark:bg-neutral-800 border-neutral-300 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200 shadow-sm"
                        : "bg-transparent border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Checklist Coverage progress indicator */}
            <div className="flex items-center justify-between text-xs text-neutral-450">
              <span>Coverage Match Rate: <b>{master_validation.coverage_pct}%</b> ({master_validation.found_count} / {master_validation.issues.length + master_validation.missing_count} fields)</span>
            </div>

            <div className="overflow-x-auto max-h-[500px] overflow-y-auto pr-1">
              <table className="w-full text-left apple-table table-fixed">
                <thead>
                  <tr className="border-b border-neutral-900/60 bg-neutral-900/10">
                    <th className="py-3 px-4 text-neutral-500 font-semibold uppercase tracking-wider text-xs w-[40%] text-left">Variable Symbol</th>
                    <th className="py-3 px-4 text-neutral-500 font-semibold uppercase tracking-wider text-xs w-[20%] text-left">Group Category</th>
                    <th className="py-3 px-4 text-neutral-500 font-semibold uppercase tracking-wider text-xs w-[25%] text-left">Requirements</th>
                    <th className="py-3 px-4 text-neutral-500 font-semibold uppercase tracking-wider text-xs w-[15%] text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-900/60">
                  {filteredVariables.map((issue: any, idx: number) => (
                    <tr key={idx} className="hover:bg-neutral-900/30 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-white text-xs text-left truncate" title={issue.variable}>{issue.variable}</td>
                      <td className="py-3 px-4 text-neutral-450 text-xs text-left truncate">{issue.category}</td>
                      <td className="py-3 px-4 text-neutral-450 text-xs text-left truncate">
                        {issue.required ? "Mandatory Core" : "Optional field"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span 
                          title={issue.status === "WARNING" && issue.details ? issue.details : undefined}
                          className={`${
                            issue.status === "MISSING"
                              ? (issue.required ? "badge-apple-fail ml-auto inline-block" : "badge-apple-warn ml-auto inline-block")
                              : issue.status === "WARNING"
                              ? "badge-apple-warn cursor-help ml-auto inline-block"
                              : issue.status === "UNEXPECTED"
                              ? "badge-apple-neutral ml-auto inline-block"
                              : "badge-apple-pass ml-auto inline-block"
                          }`}
                        >
                          {issue.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {filteredVariables.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-neutral-600">No variables match the selected filter conditions.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* SPSS Metadata Tab */}
        {activeTab === "metadata" && (
          <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-neutral-900 pb-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450">SPSS Dictionary Integrity Logs</h3>
              <span className="text-xs text-neutral-550 font-mono">
                Dict coverage: {metadata_validation.coverage_pct}%
              </span>
            </div>
            
            {metadata_validation.issues.length > 0 ? (
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto pr-1">
                <table className="w-full text-left apple-table">
                  <thead>
                    <tr>
                      <th className="pb-3 text-neutral-500">Variable</th>
                      <th className="pb-3 text-neutral-500">Dictionary Rule</th>
                      <th className="pb-3 text-neutral-500">Observation & Details</th>
                      <th className="pb-3 text-neutral-500 text-right">Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metadata_validation.issues.map((issue: any, idx: number) => (
                      <tr key={idx}>
                        <td className="py-3.5 font-mono font-medium text-white text-xs">{issue.variable}</td>
                        <td className="py-3.5 font-mono text-xs text-blue-400">{issue.issue_type}</td>
                        <td className="py-3.5 text-neutral-300">{issue.details}</td>
                        <td className="py-3.5 text-right">
                          <span className={issue.severity === "FAIL" ? "badge-apple-fail" : "badge-apple-warn"}>
                            {issue.severity}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-14 text-center text-neutral-550 space-y-2">
                <CheckCircle2 className="h-8 w-8 text-emerald-450 mx-auto stroke-[1.5]" />
                <p className="text-xs font-medium text-neutral-450">All column dictionary definitions match requirements.</p>
              </div>
            )}
          </div>
        )}

        {/* Intelligent Binary Tab */}
        {activeTab === "binary" && (
          <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-6">
            
            <div className="flex justify-between items-center border-b border-neutral-900 pb-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450">Binary Coding Alignment Rules</h3>
              <div className="flex gap-4 text-[10px] font-mono text-neutral-500">
                <span>Pass: <b className="text-emerald-450">{binary_validation.pass_count}</b></span>
                <span>Warnings: <b className="text-amber-450">{binary_validation.warning_count}</b></span>
                <span>Fails: <b className="text-rose-550">{binary_validation.fail_count}</b></span>
              </div>
            </div>

            {binary_validation.issues.length > 0 ? (
              <div className="space-y-6 animate-apple-fade">
                
                {/* Success Summary Card */}
                {fixResult && (
                  <div className="bg-emerald-950/20 border border-emerald-500/20 p-6 rounded-2xl space-y-4 animate-apple-fade">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-emerald-500/10 rounded-lg">
                        <CheckCircle2 className="h-6 w-6 text-emerald-450 stroke-[2]" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white">Auto-Fix Campaign Executed</h4>
                        <p className="text-xs text-neutral-400">Dataset updated and downloaded successfully.</p>
                      </div>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3 pt-2">
                      {Object.entries(fixResult.fixes_applied).map(([variable, rule]: any) => (
                        <div key={variable} className="bg-neutral-900/40 border border-neutral-850 p-3 rounded-xl flex items-center gap-2">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                          <div className="min-w-0">
                            <p className="font-mono text-xs font-semibold text-white truncate">{variable}</p>
                            <p className="text-[10px] text-neutral-550 font-mono truncate">{rule}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-3 pt-2">
                      <a
                        href={fixResult.download_url}
                        download={fixResult.corrected_file}
                        className="apple-btn-secondary py-1.5 px-3.5 text-xs text-emerald-400 bg-emerald-500/10 border-emerald-500/20 hover:bg-emerald-500/25 hover:border-emerald-500/35 font-medium rounded-full shadow-sm flex items-center gap-1.5 transition-all"
                      >
                        Download Dataset Again
                      </a>
                      <button
                        onClick={() => setFixResult(null)}
                        className="apple-btn-secondary py-1.5 px-3.5 text-xs text-neutral-400 bg-neutral-900 border-neutral-800 hover:text-white hover:border-neutral-700 font-medium rounded-full flex items-center gap-1.5 transition-all"
                      >
                        Dismiss Summary
                      </button>
                    </div>
                  </div>
                )}

                {/* Explanation Card */}
                <div className="p-4 bg-neutral-900/40 border border-neutral-850 text-neutral-400 text-xs rounded-xl flex items-start gap-3">
                  <ShieldCheck className="h-5 w-5 text-emerald-450 shrink-0 mt-0.5" />
                  <p className="leading-relaxed">
                    <b>Interactive Fix Campaign:</b> Preview suggested binary recodings to match standard <b>0 (No)</b> / <b>1 (Yes)</b> coding conventions. Toggle checkboxes to selectively approve variables, review their estimated row impact and severity, then apply fixes below.
                  </p>
                </div>

                {/* Action Bar/Panel */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-neutral-900/20 border border-neutral-900 rounded-xl">
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-white">Select Recodes to Apply</p>
                    <p className="text-[11px] text-neutral-550">
                      {selectedFixes.length} of {checkableIssues.length} warnings selected
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={toggleAll}
                      className="apple-btn-secondary px-3.5 py-1.5 text-xs text-neutral-400 hover:text-white transition-all font-medium rounded-full bg-neutral-900 border-neutral-800"
                    >
                      {allChecked ? "Deselect All" : "Select All"}
                    </button>
                    <button
                      onClick={handleApproveFixes}
                      disabled={fixing || selectedFixes.length === 0}
                      className={`px-4 py-1.5 text-xs font-semibold rounded-full shadow-sm flex items-center gap-1.5 transition-all ${
                        selectedFixes.length === 0 || fixing
                          ? "bg-neutral-800 text-neutral-500 border border-neutral-700 cursor-not-allowed"
                          : "bg-emerald-500 hover:bg-emerald-600 text-white font-medium shadow-emerald-500/10 hover:shadow-emerald-500/20 cursor-pointer"
                      }`}
                    >
                      {fixing ? (
                        <>
                          <span className="h-3 w-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                          <span>Applying...</span>
                        </>
                      ) : (
                        <>
                          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <path d="M12 15V3m0 12l-4-4m4 4l4-4M4 17h16" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                          <span>Approve Fixes & Download</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Interactive Fix Preview Table */}
                <div className="overflow-x-auto border border-neutral-900 rounded-xl">
                  <table className="w-full text-left apple-table border-collapse">
                    <thead>
                      <tr className="border-b border-neutral-900 bg-neutral-900/10">
                        <th className="py-3 px-4 w-12 text-neutral-500">
                          <input
                            type="checkbox"
                            checked={allChecked}
                            onChange={toggleAll}
                            disabled={checkableIssues.length === 0}
                            className="rounded border-neutral-800 bg-neutral-950 text-emerald-500 focus:ring-emerald-500/20 cursor-pointer h-3.5 w-3.5"
                          />
                        </th>
                        <th className="py-3 px-4 text-neutral-500 text-xs font-semibold uppercase tracking-wider">Variable</th>
                        <th className="py-3 px-4 text-neutral-500 text-xs font-semibold uppercase tracking-wider">Detected Coding</th>
                        <th className="py-3 px-4 text-neutral-500 text-xs font-semibold uppercase tracking-wider">Recommended Fix</th>
                        <th className="py-3 px-4 text-neutral-500 text-xs font-semibold uppercase tracking-wider">Rows Impact</th>
                        <th className="py-3 px-4 text-neutral-500 text-xs font-semibold uppercase tracking-wider">Severity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-900/60">
                      {binary_validation.issues.map((issue: any, idx: number) => {
                        const isCheckable = issue.severity === "WARNING" && issue.suggested_fix;
                        const isChecked = selectedFixes.includes(issue.variable);
                        const impact = issue.impact_data;
                        
                        let severityClass = "bg-neutral-900 text-neutral-400 border-neutral-850";
                        let severityLabel = "Low";
                        
                        if (impact) {
                          if (impact.severity === "HIGH") {
                            severityClass = "bg-rose-500/10 text-rose-500 border-rose-500/20";
                            severityLabel = "High";
                          } else if (impact.severity === "MEDIUM") {
                            severityClass = "bg-amber-500/10 text-amber-500 border-amber-500/20";
                            severityLabel = "Medium";
                          } else if (impact.severity === "LOW") {
                            severityClass = "bg-emerald-500/10 text-emerald-450 border-emerald-500/20";
                            severityLabel = "Low";
                          }
                        } else if (issue.severity === "FAIL") {
                          severityClass = "bg-rose-500/10 text-rose-500 border-rose-500/20";
                          severityLabel = "Fatal Fail";
                        }

                        return (
                          <tr 
                            key={idx} 
                            className={`transition-colors duration-150 hover:bg-neutral-900/20 ${
                              isChecked ? "bg-emerald-500/[0.02]" : ""
                            }`}
                          >
                            <td className="py-3 px-4">
                              {isCheckable ? (
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => toggleFix(issue.variable)}
                                  className="rounded border-neutral-800 bg-neutral-950 text-emerald-500 focus:ring-emerald-500/20 cursor-pointer h-3.5 w-3.5"
                                />
                              ) : (
                                <span className="flex items-center justify-center w-3.5 h-3.5" title="Requires manual data cleaning">
                                  <AlertTriangle className="h-3.5 w-3.5 text-rose-500" />
                                </span>
                              )}
                            </td>
                            <td className="py-3.5 px-4 font-mono font-medium text-white text-xs">
                              {issue.variable}
                            </td>
                            <td className="py-3.5 px-4 font-mono text-xs text-neutral-400">
                              {issue.detected_coding}
                            </td>
                            <td className="py-3.5 px-4 font-mono text-xs text-emerald-400 font-bold">
                              {issue.suggested_fix ? (
                                <span>{issue.suggested_fix}</span>
                              ) : (
                                <span className="text-neutral-550 font-normal">Manual clean required</span>
                              )}
                            </td>
                            <td className="py-3.5 px-4 text-xs text-neutral-300">
                              {impact ? (
                                <span className="font-medium">
                                  {impact.affected_rows.toLocaleString()} <span className="text-neutral-500">({impact.affected_pct}%)</span>
                                </span>
                              ) : issue.severity === "FAIL" ? (
                                <span className="text-neutral-500">N/A (Multi-state)</span>
                              ) : (
                                <span className="text-neutral-550 italic">Calculating...</span>
                              )}
                            </td>
                            <td className="py-3.5 px-4">
                              <span className={`px-2 py-0.5 text-[10px] font-semibold tracking-wide rounded-full border ${severityClass}`}>
                                {severityLabel}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

              </div>
            ) : (
              <div className="py-14 text-center text-neutral-550 space-y-2">
                <CheckCircle2 className="h-8 w-8 text-emerald-450 mx-auto stroke-[1.5]" />
                <p className="text-xs font-medium text-neutral-450">All binary metrics are correctly saved in standard 0/1 formats.</p>
              </div>
            )}
          </div>
        )}

        {/* Completeness Tab */}
        {activeTab === "completeness" && (
          <div className="space-y-6">
            <div className="grid gap-6 md:grid-cols-4">
              <div className="bg-neutral-950 border border-neutral-900 p-5 rounded-2xl">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Severity</p>
                <div className="mt-3">
                  <span className={completenessData.status === "FAIL" ? "badge-apple-fail" : completenessData.status === "WARNING" ? "badge-apple-warn" : "badge-apple-neutral"}>
                    {completenessData.status}
                  </span>
                </div>
              </div>
              <div className="bg-neutral-950 border border-neutral-900 p-5 rounded-2xl">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Respondents</p>
                <p className="text-2xl font-semibold text-white tracking-tight mt-2">{completenessData.total_respondents?.toLocaleString?.() || 0}</p>
              </div>
              <div className="bg-neutral-950 border border-neutral-900 p-5 rounded-2xl">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Analysis Variables</p>
                <p className="text-2xl font-semibold text-white tracking-tight mt-2">{completenessData.total_analysis_variables}</p>
              </div>
              <div className="bg-neutral-950 border border-neutral-900 p-5 rounded-2xl">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Fully Missing</p>
                <p className="text-2xl font-semibold text-rose-500 tracking-tight mt-2">
                  {completenessData.fully_missing_respondents_count} <span className="text-sm text-neutral-500">({completenessData.fully_missing_respondents_pct}%)</span>
                </p>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450 border-b border-neutral-900 pb-3">
                  Response Coverage Distribution
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left apple-table">
                    <thead>
                      <tr>
                        <th className="pb-2 text-neutral-500">Coverage Band</th>
                        <th className="pb-2 text-neutral-500 text-right">Respondents</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(completenessData.coverage_distribution || []).map((item: any, idx: number) => (
                        <tr key={idx}>
                          <td className="py-2.5 text-neutral-250 text-xs font-medium">{item.band}</td>
                          <td className="py-2.5 text-right text-white font-semibold">{item.respondents?.toLocaleString?.() || 0}</td>
                        </tr>
                      ))}
                      {(completenessData.coverage_distribution || []).length === 0 && (
                        <tr>
                          <td colSpan={2} className="py-8 text-center text-neutral-600 text-xs">
                            No coverage distribution available for this run.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450 border-b border-neutral-900 pb-3">
                  Completeness Signal
                </h3>
                <div className="space-y-3 text-xs">
                  <div className="p-3 bg-neutral-900/30 border border-neutral-900 rounded-xl flex justify-between">
                    <span className="text-neutral-450">Threshold 1</span>
                    <span className="text-neutral-200">&lt; 1% = INFO</span>
                  </div>
                  <div className="p-3 bg-neutral-900/30 border border-neutral-900 rounded-xl flex justify-between">
                    <span className="text-neutral-450">Threshold 2</span>
                    <span className="text-neutral-200">1% - 3% = WARNING</span>
                  </div>
                  <div className="p-3 bg-neutral-900/30 border border-neutral-900 rounded-xl flex justify-between">
                    <span className="text-neutral-450">Threshold 3</span>
                    <span className="text-neutral-200">&gt; 3% = FAIL</span>
                  </div>
                  <div className="pt-2 text-neutral-500">
                    Quality penalty from completeness check:
                    <span className="ml-1 font-semibold text-rose-500">-{completenessData.quality_score_penalty || 0} pts</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
              <div className="flex justify-between items-center border-b border-neutral-900 pb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450">Fully Missing Respondent List</h3>
                <span className="text-[10px] font-mono text-neutral-500">
                  {completenessData.fully_missing_respondents_count} respondents
                </span>
              </div>

              {(completenessData.fully_missing_respondents || []).length > 0 ? (
                <div className="overflow-x-auto max-h-[460px] overflow-y-auto pr-1">
                  <table className="w-full text-left apple-table">
                    <thead>
                      <tr>
                        <th className="pb-2 text-neutral-500">Respondent ID</th>
                        <th className="pb-2 text-neutral-500">Country</th>
                        <th className="pb-2 text-neutral-500">Brand</th>
                        <th className="pb-2 text-neutral-500">Missing Variables</th>
                        <th className="pb-2 text-neutral-500 text-right">Missing %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(completenessData.fully_missing_respondents || []).map((row: any, idx: number) => (
                        <tr key={idx}>
                          <td className="py-2.5 font-mono font-medium text-white text-xs">{row.respondent_id}</td>
                          <td className="py-2.5 text-neutral-350 text-xs">{row.country || "-"}</td>
                          <td className="py-2.5 text-neutral-350 text-xs">{row.brand || "-"}</td>
                          <td className="py-2.5 text-neutral-250 text-xs">{row.missing_analysis_variables}</td>
                          <td className="py-2.5 text-right text-rose-500 font-semibold text-xs">{row.missing_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-14 text-center text-neutral-550 space-y-2">
                  <CheckCircle2 className="h-8 w-8 text-emerald-450 mx-auto stroke-[1.5]" />
                  <p className="text-xs font-medium text-neutral-450">No fully missing respondents were detected for this run.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Nulls & Datatypes Tab */}
        {activeTab === "null_types" && (
          <div className="space-y-6">
            <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
              <div className="flex justify-between items-center border-b border-neutral-900 pb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450">Top 10 Variables with Most Missing Values</h3>
                <span className="text-[10px] font-mono text-neutral-500">Quick triage view</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left apple-table">
                  <thead>
                    <tr>
                      <th className="pb-2 text-neutral-500">Rank</th>
                      <th className="pb-2 text-neutral-500">Variable</th>
                      <th className="pb-2 text-neutral-500">Missing Cells</th>
                      <th className="pb-2 text-neutral-500">Missing Rate</th>
                      <th className="pb-2 text-neutral-500 text-right">Data Health</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topNullVariables.map((item: any, idx: number) => (
                      <tr key={item.variable || idx}>
                        <td className="py-2.5 text-neutral-500 text-xs">#{idx + 1}</td>
                        <td className="py-2.5 font-mono font-medium text-white text-xs">{item.variable}</td>
                        <td className="py-2.5 text-neutral-350 text-xs">{item.null_count?.toLocaleString?.() || 0}</td>
                        <td className="py-2.5 text-neutral-200 text-xs font-semibold">{item.null_pct}%</td>
                        <td className="py-2.5 text-right">
                          <span className={item.status === "RED" ? "badge-apple-fail" : item.status === "YELLOW" ? "badge-apple-warn" : "badge-apple-pass"}>
                            {item.status === "RED" ? "High Missing" : item.status === "YELLOW" ? "Moderate Missing" : "Healthy"}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {topNullVariables.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-neutral-600 text-xs">
                          No null analysis results available for this report.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
            {/* Null Analysis with inline slider bars */}
            <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
              <div className="flex justify-between items-center border-b border-neutral-900 pb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450">Missing Data by Variable</h3>
                <div className="flex gap-3 text-[10px] font-mono text-neutral-500">
                  <span>Healthy: <b className="text-emerald-450">{null_analysis.green_count}</b></span>
                  <span>Moderate Missing: <b className="text-amber-450">{null_analysis.yellow_count}</b></span>
                  <span>High Missing: <b className="text-rose-500">{null_analysis.red_count}</b></span>
                </div>
              </div>

              <div className="overflow-x-auto max-h-[400px] overflow-y-auto pr-1">
                <table className="w-full text-left apple-table">
                  <thead>
                    <tr>
                      <th className="pb-2 text-neutral-500">Variable</th>
                      <th className="pb-2 text-neutral-500">Missing Cells</th>
                      <th className="pb-2 text-neutral-500">Missing Rate Bar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {null_analysis.variables.map((item: any, idx: number) => {
                      // Color based on status
                      let barColor = "bg-emerald-500";
                      if (item.status === "RED") barColor = "bg-rose-500";
                      else if (item.status === "YELLOW") barColor = "bg-amber-500";

                      return (
                        <tr key={idx}>
                          <td className="py-2.5 font-mono font-medium text-neutral-300 text-xs">{item.variable}</td>
                          <td className="py-2.5 text-neutral-450">{item.null_pct}% ({item.null_count.toLocaleString()})</td>
                          <td className="py-2.5 w-32">
                            <div className="h-1.5 w-full bg-neutral-900 rounded-full overflow-hidden">
                              <div className={`h-full ${barColor} rounded-full`} style={{ width: `${item.null_pct}%` }}></div>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Datatype mismatches */}
            <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450 border-b border-neutral-900 pb-3">Datatype Schema Divergence</h3>
              
              {datatype_validation.length > 0 ? (
                <div className="overflow-x-auto max-h-[400px] overflow-y-auto pr-1">
                  <table className="w-full text-left apple-table">
                    <thead>
                      <tr>
                        <th className="pb-2 text-neutral-500">Variable</th>
                        <th className="pb-2 text-neutral-500">Expected Type</th>
                        <th className="pb-2 text-neutral-500">Actual Type</th>
                        <th className="pb-2 text-neutral-500 text-right">Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {datatype_validation.map((issue: any, idx: number) => (
                        <tr key={idx}>
                          <td className="py-2.5 font-mono font-medium text-white text-xs">{issue.variable}</td>
                          <td className="py-2.5 font-mono text-neutral-500">{issue.expected_type}</td>
                          <td className="py-2.5 font-mono text-rose-400 font-semibold">{issue.actual_type}</td>
                          <td className="py-2.5 text-right text-rose-500 font-semibold text-xs">{issue.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-14 text-center text-neutral-550 space-y-2">
                  <CheckCircle2 className="h-8 w-8 text-emerald-450 mx-auto stroke-[1.5]" />
                  <p className="text-xs font-medium text-neutral-450">All parsed datatypes align with expected schema mappings.</p>
                </div>
              )}
            </div>
            </div>
          </div>
        )}

        {/* Duplicates Tab */}
        {activeTab === "duplicates" && (
          <div className="grid gap-6 md:grid-cols-2">
            {/* Duplicates counters */}
            <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450 border-b border-neutral-900 pb-3">Duplicates Records Summary</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3.5 bg-neutral-900/30 rounded-xl border border-neutral-900">
                  <div className="flex flex-col">
                    <span className="text-neutral-300 text-xs font-medium">Duplicate Rows</span>
                    <span className="text-[9px] text-neutral-550 mt-0.5">Identical across all variables</span>
                  </div>
                  <span className={`font-semibold text-xs ${duplicate_analysis.duplicate_rows_count > 0 ? "text-rose-500" : "text-emerald-450"}`}>
                    {duplicate_analysis.duplicate_rows_count} records
                  </span>
                </div>

                <div className="flex justify-between items-center p-3.5 bg-neutral-900/30 rounded-xl border border-neutral-900">
                  <div className="flex flex-col">
                    <span className="text-neutral-300 text-xs font-medium">Duplicate Respondent IDs</span>
                    <span className="text-[9px] text-neutral-550 mt-0.5">Key: {duplicate_analysis.respondent_id_col || "None"}</span>
                  </div>
                  <span className={`font-semibold text-xs ${duplicate_analysis.duplicate_respondents_count > 0 ? "text-rose-500" : "text-emerald-450"}`}>
                    {duplicate_analysis.duplicate_respondents_count} IDs
                  </span>
                </div>

                <div className="flex justify-between items-center p-3.5 bg-neutral-900/30 rounded-xl border border-neutral-900">
                  <div className="flex flex-col">
                    <span className="text-neutral-300 text-xs font-medium">Duplicate Stack Keys</span>
                    <span className="text-[9px] text-neutral-550 mt-0.5">Combination: Key + Brand Dimension</span>
                  </div>
                  <span className={`font-semibold text-xs ${duplicate_analysis.duplicate_brand_rows_count > 0 ? "text-rose-500" : "text-emerald-450"}`}>
                    {duplicate_analysis.duplicate_brand_rows_count} records
                  </span>
                </div>
              </div>
            </div>

            {/* Constants and empties columns */}
            <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450 border-b border-neutral-900 pb-3">Constant or Empty Columns</h3>
              {empty_variables.length > 0 ? (
                <div className="overflow-x-auto max-h-[350px] overflow-y-auto pr-1">
                  <table className="w-full text-left apple-table">
                    <thead>
                      <tr>
                        <th className="pb-2 text-neutral-500">Variable</th>
                        <th className="pb-2 text-neutral-500">Alert Type</th>
                        <th className="pb-2 text-neutral-500 text-right">Fixed Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {empty_variables.map((item: any, idx: number) => (
                        <tr key={idx}>
                          <td className="py-2.5 font-mono font-medium text-white text-xs">{item.variable}</td>
                          <td className="py-2.5">
                            <span className={item.type === "EMPTY" ? "badge-apple-fail" : "badge-apple-warn"}>
                              {item.type}
                            </span>
                          </td>
                          <td className="py-2.5 text-right font-mono text-neutral-500">{item.constant_value || "Null"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-14 text-center text-neutral-550 space-y-2">
                  <CheckCircle2 className="h-8 w-8 text-emerald-450 mx-auto stroke-[1.5]" />
                  <p className="text-xs font-medium text-neutral-450">No constant or empty variables detected.</p>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
