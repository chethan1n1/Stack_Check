import { useEffect } from "react";
import { useAppStore } from "../store/useAppStore";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { FileSpreadsheet, History, Layers, ArrowUpRight } from "lucide-react";
import { api } from "../services/api";

export default function Dashboard() {
  const { history, loadHistory, profiles, loadProfiles, setActiveReport, setActivePage } = useAppStore();

  useEffect(() => {
    loadHistory();
    loadProfiles();
  }, []);

  const totalChecks = history.length;
  const passes = history.filter(h => h.result === "PASS").length;
  const warnings = history.filter(h => h.result === "WARNING").length;
  const fails = history.filter(h => h.result === "FAIL").length;
  
  const averageScore = totalChecks 
    ? Math.round(history.reduce((acc, h) => acc + h.score, 0) / totalChecks) 
    : 0;

  // Chart 1: Issue Breakdown
  const latestRun = history[0];
  const latestSummary = latestRun?.summary_data;
  
  const issueBreakdownData = latestSummary ? [
    { name: "Missing Vars", count: latestSummary.missing_vars },
    { name: "Binary Warnings", count: latestSummary.binary_warnings },
    { name: "Binary Fails", count: latestSummary.binary_fails },
    { name: "Null Alerts", count: latestSummary.null_red_count }
  ] : [
    { name: "Missing Vars", count: 0 },
    { name: "Binary Warnings", count: 0 },
    { name: "Binary Fails", count: 0 },
    { name: "Null Alerts", count: 0 }
  ];

  // Chart 2: Data Quality Trend
  const trendData = history.slice(0, 10).reverse().map(h => ({
    name: h.dataset_name.length > 15 ? h.dataset_name.substring(0, 10) + "..." : h.dataset_name,
    score: h.score
  }));

  const handleRowClick = async (item: any) => {
    try {
      const detailReport = await api.getReportById(item.id);
      setActiveReport(detailReport);
      setActivePage("validation-center");
    } catch (err) {
      alert("Failed to retrieve the detailed validation report.");
    }
  };

  return (
    <div className="space-y-10 animate-apple-fade">
      
      {/* Apple-style Page Header */}
      <div className="border-b border-neutral-900 pb-5">
        <h1 className="text-3xl font-semibold tracking-tight text-white">
          Overview
        </h1>
        <p className="text-sm text-neutral-500 mt-1">Data Processing audit trail metrics & quality indicators.</p>
      </div>

      {/* KPI Grid */}
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Metric 1 */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl flex flex-col justify-between min-h-[120px]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Runs</span>
          <h3 className="text-4xl font-semibold text-white tracking-tight mt-3">{totalChecks}</h3>
          <p className="text-[11px] text-neutral-550 mt-1">Stacked files validated</p>
        </div>

        {/* Metric 2 */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl flex flex-col justify-between min-h-[120px]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Quality Index</span>
          <h3 className="text-4xl font-semibold text-white tracking-tight mt-3">
            {averageScore}<span className="text-lg text-neutral-600 font-normal">/100</span>
          </h3>
          <p className="text-[11px] text-neutral-550 mt-1">Global average quality score</p>
        </div>

        {/* Metric 3 */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl flex flex-col justify-between min-h-[120px]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Success Metrics</span>
          <div className="flex items-baseline gap-3 mt-3">
            <span className="text-3xl font-semibold text-emerald-450 tracking-tight">{passes}</span>
            <span className="text-[10px] text-neutral-650 font-medium uppercase">pass</span>
            <span className="text-3xl font-semibold text-amber-450 tracking-tight ml-2">{warnings}</span>
            <span className="text-[10px] text-neutral-650 font-medium uppercase">warn</span>
          </div>
          <p className="text-[11px] text-neutral-550 mt-1">Runs without critical failure</p>
        </div>

        {/* Metric 4 */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl flex flex-col justify-between min-h-[120px]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Rejected Files</span>
          <h3 className="text-4xl font-semibold text-rose-500 tracking-tight mt-3">{fails}</h3>
          <p className="text-[11px] text-neutral-550 mt-1">Rework required (Score &lt; 60)</p>
        </div>
      </div>

      {/* Visualizations Section */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Score Trend Area Chart */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450 mb-6 flex items-center gap-2">
            <History className="h-3.5 w-3.5 text-neutral-500" /> Validation Quality Trend
          </h3>
          <div className="h-60">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="scoreGlow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0071e3" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#0071e3" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#1c1c1e" strokeDasharray="0" vertical={false} />
                  <XAxis dataKey="name" stroke="#525252" fontSize={9} axisLine={false} tickLine={false} dy={10} />
                  <YAxis stroke="#525252" fontSize={9} domain={[0, 100]} axisLine={false} tickLine={false} dx={-5} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: "rgba(10, 10, 10, 0.85)", 
                      border: "1px solid rgba(255,255,255,0.08)", 
                      borderRadius: "10px", 
                      backdropFilter: "blur(20px)",
                      color: "#fff",
                      fontSize: "11px"
                    }} 
                  />
                  <Area type="monotone" dataKey="score" stroke="#0071e3" strokeWidth={2} fillOpacity={1} fill="url(#scoreGlow)" dot={{ r: 3.5, strokeWidth: 0, fill: "#0071e3" }} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-neutral-500 text-xs">
                No runs recorded. Validation trends will populate here.
              </div>
            )}
          </div>
        </div>

        {/* Latest Run Issues Bar Chart */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-450 mb-6 flex items-center gap-2">
            <Layers className="h-3.5 w-3.5 text-neutral-500" /> Discrepancies Distribution (Latest Run)
          </h3>
          <div className="h-60">
            {latestRun ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={issueBreakdownData}>
                  <CartesianGrid stroke="#1c1c1e" strokeDasharray="0" vertical={false} />
                  <XAxis dataKey="name" stroke="#525252" fontSize={9} axisLine={false} tickLine={false} dy={10} />
                  <YAxis stroke="#525252" fontSize={9} allowDecimals={false} axisLine={false} tickLine={false} dx={-5} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: "rgba(10, 10, 10, 0.85)", 
                      border: "1px solid rgba(255,255,255,0.08)", 
                      borderRadius: "10px", 
                      backdropFilter: "blur(20px)",
                      color: "#fff",
                      fontSize: "11px"
                    }} 
                  />
                  <Bar dataKey="count" fill="#30d158" radius={[4, 4, 0, 0]} maxBarSize={30} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-neutral-500 text-xs">
                No runs recorded. Run errors will be mapped visually.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Grid: Recent Runs Table & Active Profiles List */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Table List */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl md:col-span-2 space-y-4">
          <div className="flex justify-between items-center pb-2 border-b border-neutral-900">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 flex items-center gap-2">
              <FileSpreadsheet className="h-3.5 w-3.5 text-neutral-500" /> Recent Runs Activity
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs apple-table border-collapse">
              <thead>
                <tr>
                  <th className="pb-3 text-neutral-500 font-medium">Dataset Name</th>
                  <th className="pb-3 text-neutral-500 font-medium">Profile Template</th>
                  <th className="pb-3 text-neutral-500 font-medium">Quality Score</th>
                  <th className="pb-3 text-neutral-500 font-medium">Validation Status</th>
                  <th className="pb-3 text-neutral-500 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 5).map(item => (
                  <tr key={item.id} className="cursor-pointer group" onClick={() => handleRowClick(item)}>
                    <td className="py-3.5 font-medium text-neutral-200 max-w-[200px] truncate">{item.dataset_name}</td>
                    <td className="py-3.5 text-neutral-450">{item.profile_name}</td>
                    <td className="py-3.5 font-semibold text-white">{item.score}</td>
                    <td className="py-3.5">
                      <span className={item.result === "PASS" ? "badge-apple-pass" : item.result === "WARNING" ? "badge-apple-warn" : "badge-apple-fail"}>
                        {item.result}
                      </span>
                    </td>
                    <td className="py-3.5 text-right text-neutral-500 group-hover:text-white transition-colors">
                      <ArrowUpRight className="h-4 w-4 inline-block" />
                    </td>
                  </tr>
                ))}
                {totalChecks === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-neutral-600">No validations recorded in local database.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Profiles Sidebar panel */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 flex items-center gap-2 pb-2 border-b border-neutral-900">
            <Layers className="h-3.5 w-3.5 text-neutral-500" /> Active Tracking Profiles
          </h3>
          
          <div className="space-y-3 max-h-[260px] overflow-y-auto pr-1">
            {profiles.slice(0, 5).map(profile => (
              <div key={profile.id} className="p-3.5 bg-[#09090b] rounded-xl border border-neutral-900 flex flex-col hover:border-neutral-850 transition-colors">
                <span className="font-medium text-xs text-neutral-200">{profile.name}</span>
                <span className="text-[10px] text-neutral-500 line-clamp-1 mt-1">{profile.description || "No description."}</span>
                <div className="text-[9px] font-mono text-neutral-500 mt-2">
                  {profile.config.variables.length} expected variables
                </div>
              </div>
            ))}
            {profiles.length === 0 && (
              <div className="text-center py-10 text-neutral-650 text-xs">No active templates registered.</div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
