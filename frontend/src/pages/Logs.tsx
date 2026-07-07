import { useEffect } from "react";
import { useAppStore } from "../store/useAppStore";
import { History, FileText, FileSpreadsheet, Eye, User } from "lucide-react";
import { api } from "../services/api";

export default function Logs() {
  const { history, loadHistory, setActiveReport, setActivePage } = useAppStore();

  useEffect(() => {
    loadHistory();
  }, []);

  const handleView = async (id: number) => {
    try {
      const detailReport = await api.getReportById(id);
      setActiveReport(detailReport);
      setActivePage("validation-center");
    } catch (err) {
      alert("Failed to retrieve the detailed validation report.");
    }
  };

  return (
    <div className="space-y-6 animate-apple-fade">
      
      {/* Page Header */}
      <div className="border-b border-neutral-900 pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-white">
          Audit Trail
        </h1>
        <p className="text-xs text-neutral-500 mt-1">Review past validation wave runs and extract reports.</p>
      </div>

      <div className="bg-neutral-950 border border-neutral-900 rounded-xl overflow-hidden shadow-sm">
        
        {/* Sub header bar */}
        <div className="px-5 py-4 border-b border-neutral-900 flex items-center gap-2">
          <History className="h-4 w-4 text-neutral-400 stroke-[1.5]" />
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">Wave Run Registry Logs</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-[11px] border-collapse">
            <thead>
              <tr className="border-b border-neutral-900 bg-neutral-900/10 text-neutral-500 font-medium">
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-neutral-500 text-[10px]">Dataset File</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-neutral-500 text-[10px]">Profile Template</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-neutral-500 text-[10px]">Operator ID</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-neutral-500 text-[10px] text-center">Score</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-neutral-500 text-[10px]">Result Status</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-neutral-500 text-[10px]">Validated At</th>
                <th className="px-4 py-3 font-semibold uppercase tracking-wider text-neutral-500 text-[10px] text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-900/60">
              {history.map(item => (
                <tr key={item.id} className="hover:bg-neutral-900/30 transition-colors">
                  <td className="px-4 py-3 font-medium text-neutral-200 max-w-[160px] truncate">{item.dataset_name}</td>
                  <td className="px-4 py-3 text-neutral-450">{item.profile_name}</td>
                  <td className="px-4 py-3 text-neutral-450">
                    <div className="flex items-center gap-1">
                      <User className="h-3 w-3 text-neutral-600" />
                      <span>{item.username}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center font-semibold text-white font-mono text-xs">{item.score}</td>
                  <td className="px-4 py-3">
                    <span className={
                      item.result === "PASS"
                        ? "badge-apple-pass text-[10px] px-2 py-0.5"
                        : item.result === "WARNING"
                        ? "badge-apple-warn text-[10px] px-2 py-0.5"
                        : "badge-apple-fail"
                    }>
                      {item.result}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-neutral-550 font-mono text-[10px]">
                    {new Date(item.validation_timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => handleView(item.id)}
                        className="px-2.5 py-1 text-[10px] flex items-center gap-1 text-blue-600 dark:text-blue-400 bg-blue-500/5 dark:bg-blue-500/10 border border-blue-500/10 dark:border-blue-500/20 hover:bg-blue-500/15 dark:hover:bg-blue-500/20 hover:text-blue-500 rounded-md transition-all font-medium cursor-pointer"
                        title="Open Details Panel"
                      >
                        <Eye className="h-3 w-3 text-blue-400" />
                        <span>Inspect</span>
                      </button>
                      
                      {item.report_xlsx_path && (
                        <a
                          href={item.report_xlsx_path}
                          className="px-2.5 py-1 text-[10px] flex items-center gap-1 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5 dark:bg-emerald-500/10 border border-emerald-500/10 dark:border-emerald-500/20 hover:bg-emerald-500/15 dark:hover:bg-emerald-500/20 hover:text-emerald-500 rounded-md transition-all font-medium"
                          title="Download Excel Spreadsheet"
                        >
                          <FileSpreadsheet className="h-3 w-3 text-emerald-450" />
                          <span>Excel</span>
                        </a>
                      )}
                      
                      {item.report_pdf_path && (
                        <a
                          href={item.report_pdf_path}
                          className="px-2.5 py-1 text-[10px] flex items-center gap-1 text-rose-600 dark:text-rose-450 bg-rose-500/5 dark:bg-rose-500/10 border border-rose-500/10 dark:border-rose-500/20 hover:bg-rose-500/15 dark:hover:bg-rose-500/20 hover:text-rose-500 rounded-md transition-all font-medium"
                          title="Download PDF Document"
                        >
                          <FileText className="h-3 w-3 text-rose-450" />
                          <span>PDF</span>
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-neutral-600">
                    No validation runs registered in the history logs.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}
