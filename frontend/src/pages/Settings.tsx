import { useState } from "react";
import { Save, Database, ShieldAlert, Award, FileCheck } from "lucide-react";

export default function Settings() {
  const [dbType, setDbType] = useState("sqlite");
  const [nullWarn, setNullWarn] = useState(5.0);
  const [nullFail, setNullFail] = useState(20.0);
  
  const [penaltyCore, setPenaltyCore] = useState(10);
  const [penaltyOpt, setPenaltyOpt] = useState(2);
  const [penaltyBinWarn, setPenaltyBinWarn] = useState(1);
  const [penaltyBinFail, setPenaltyBinFail] = useState(5);
  
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-10 animate-apple-fade">
      
      {/* Page Header */}
      <div className="border-b border-neutral-900 pb-5">
        <h1 className="text-3xl font-semibold tracking-tight text-white">System Settings</h1>
        <p className="text-sm text-neutral-500 mt-1">Configure database connections, validation penalties, and null thresholds.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-8">
        
        {/* Settings Group 1: Database */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-5">
          <div className="flex items-center gap-2.5 pb-3 border-b border-neutral-900">
            <Database className="h-4.5 w-4.5 text-neutral-450" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Database Core</h3>
          </div>
          
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs">
            <div className="space-y-1">
              <h4 className="font-semibold text-white">Active Database Connector</h4>
              <p className="text-neutral-500 max-w-sm leading-relaxed">StackCheck saves validation historical runs locally on the offline compiler database by default.</p>
            </div>
            <select
              value={dbType}
              onChange={(e) => setDbType(e.target.value)}
              className="apple-select min-w-[200px]"
            >
              <option value="sqlite">SQLite (Local Standalone)</option>
              <option value="postgresql">PostgreSQL (Enterprise Server)</option>
            </select>
          </div>
        </div>

        {/* Settings Group 2: Scoring Weights */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-5">
          <div className="flex items-center gap-2.5 pb-3 border-b border-neutral-900">
            <Award className="h-4.5 w-4.5 text-neutral-450" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Deduction Weights</h3>
          </div>
          
          <p className="text-xs text-neutral-500 leading-relaxed pb-2">
            Configure point deductions subtracted from 100 for each dataset validation discrepancy identified.
          </p>

          <div className="space-y-4">
            {[
              { label: "Missing Core Variable Penalty", value: penaltyCore, setter: setPenaltyCore, unit: "pts" },
              { label: "Missing Optional Variable Penalty", value: penaltyOpt, setter: setPenaltyOpt, unit: "pts" },
              { label: "Binary Coding Warning Penalty (Recodable)", value: penaltyBinWarn, setter: setPenaltyBinWarn, unit: "pts" },
              { label: "Binary Coding Failure Penalty (Incompatible)", value: penaltyBinFail, setter: setPenaltyBinFail, unit: "pts" }
            ].map((row, idx) => (
              <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs py-2 border-b border-neutral-900 last:border-b-0">
                <span className="font-medium text-neutral-300">{row.label}</span>
                <div className="relative flex items-center shrink-0">
                  <input
                    type="number"
                    value={row.value}
                    onChange={(e) => row.setter(Number(e.target.value))}
                    className="apple-input w-24 text-right pr-8 py-1.5 text-xs font-mono font-semibold"
                  />
                  <span className="absolute right-3 text-neutral-550 text-[10px] pointer-events-none">{row.unit}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Settings Group 3: Null Thresholds */}
        <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl space-y-5">
          <div className="flex items-center gap-2.5 pb-3 border-b border-neutral-900">
            <ShieldAlert className="h-4.5 w-4.5 text-neutral-450" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Null Cell Threshold Bounds</h3>
          </div>
          
          <p className="text-xs text-neutral-500 leading-relaxed pb-2">
            Define boundary percentages for color-flagging columns based on null values count.
          </p>

          <div className="space-y-4">
            {[
              { label: "Warning Alert (Yellow)", value: nullWarn, setter: setNullWarn },
              { label: "Critical Failure Alert (Red)", value: nullFail, setter: setNullFail }
            ].map((row, idx) => (
              <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs py-2 border-b border-neutral-900 last:border-b-0">
                <span className="font-medium text-neutral-300">{row.label}</span>
                <div className="relative flex items-center shrink-0">
                  <input
                    type="number"
                    step="0.1"
                    value={row.value}
                    onChange={(e) => row.setter(Number(e.target.value))}
                    className="apple-input w-24 text-right pr-8 py-1.5 text-xs font-mono font-semibold"
                  />
                  <span className="absolute right-3 text-neutral-550 text-[10px] pointer-events-none">%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Submit Actions */}
        <div className="flex items-center gap-4 pt-4">
          <button
            type="submit"
            className="apple-btn-primary px-6 py-2.5 font-semibold text-xs uppercase tracking-wider"
          >
            <Save className="h-3.5 w-3.5 fill-black" /> Save Preferences
          </button>
          
          {saved && (
            <p className="text-xs font-semibold text-emerald-450 flex items-center gap-1.5 animate-pulse">
              <FileCheck className="h-4 w-4" /> Preferences applied to compiler database.
            </p>
          )}
        </div>

      </form>
    </div>
  );
}
