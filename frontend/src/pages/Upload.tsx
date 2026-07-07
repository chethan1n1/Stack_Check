import { useState, useEffect } from "react";
import { useAppStore } from "../store/useAppStore";
import { UploadCloud, File, AlertCircle, Check, Play, X, Plus } from "lucide-react";
import { api, MappingPrecheckResponse } from "../services/api";

export default function Upload() {
  const {
    profiles,
    loadProfiles,
    runValidation,
    mappingReview,
    mappingOverrides,
    mappingWaivers,
    manuallyAddedVariables,
    setMappingReview,
    setMappingOverrides,
    setMappingWaivers,
    addManualVariable,
    removeManualVariable,
    clearMappingState,
  } = useAppStore();

  const [selectedProfileId, setSelectedProfileId] = useState<string>("");
  const [datasetFile, setDatasetFile] = useState<File | null>(null);
  const [specFile, setSpecFile] = useState<File | null>(null);
  const [username, setUsername] = useState<string>("DP Operator");

  const [localLoading, setLocalLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [errorText, setErrorText] = useState<string | null>(null);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [requiredOnly, setRequiredOnly] = useState(false);
  const [unmatchedOnly, setUnmatchedOnly] = useState(false);
  const [lowConfidenceOnly, setLowConfidenceOnly] = useState(false);
  const [mappingSearch, setMappingSearch] = useState("");
  const [requiredOverrides, setRequiredOverrides] = useState<Record<string, boolean>>({});
  
  // Manual variable addition form state
  const [showAddVariableForm, setShowAddVariableForm] = useState(false);
  const [addVarName, setAddVarName] = useState("");
  const [addVarRequired, setAddVarRequired] = useState(false);

  useEffect(() => {
    loadProfiles();
  }, []);

  // Update pipeline step based on the status text matching
  useEffect(() => {
    if (statusText.includes("Ingesting files")) {
      setPipelineStep(1);
    } else if (statusText.includes("Parsing dataset")) {
      setPipelineStep(2);
    } else if (statusText.includes("Scanning variables")) {
      setPipelineStep(3);
    } else if (statusText.includes("Preparing DP-to-dataset mapping suggestions")) {
      setPipelineStep(4);
    } else if (statusText.includes("Finalizing mapping review workspace")) {
      setPipelineStep(5);
    } else if (statusText.includes("Analyzing binary")) {
      setPipelineStep(4);
    } else if (statusText.includes("Calculating quality")) {
      setPipelineStep(5);
    }
  }, [statusText]);

  const handleDatasetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setDatasetFile(e.target.files[0]);
    }
  };

  const handleSpecChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSpecFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetFile) {
      setErrorText("Please select a dataset file (.sav, .xlsx, .xls, .csv) to continue.");
      return;
    }

    setLocalLoading(true);
    setErrorText(null);
    setPipelineStep(1);

    try {
      setStatusText("Ingesting files and uploading to local server...");
      const uploadRes = await api.uploadFiles(datasetFile, specFile || undefined);

      setStatusText("Parsing dataset structures (SPSS Pyreadstat/Pandas)...");
      await new Promise(r => setTimeout(r, 650));

      setStatusText("Scanning variables and checking missing fields...");
      await new Promise(r => setTimeout(r, 650));

      setStatusText("Preparing DP-to-dataset mapping suggestions...");
      let precheck: MappingPrecheckResponse | null = null;
      try {
        const precheckPromise = api.precheckMapping({
          dataset_path: uploadRes.dataset_path,
          profile_id: selectedProfileId ? Number(selectedProfileId) : undefined,
          spec_path: uploadRes.spec_path || undefined,
        });
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error("Mapping precheck timed out. Please try again.")), 180000);
        });
        precheck = await Promise.race([precheckPromise, timeoutPromise]);
      } catch (mappingErr: any) {
        const msg = String(mappingErr?.message || "");
        // Backward-compatible fallback for environments with old backend routes.
        if (msg.toLowerCase().includes("not found")) {
          setStatusText("Mapping review endpoint unavailable, running direct validation...");
          await runValidation({
            dataset_path: uploadRes.dataset_path,
            profile_id: selectedProfileId ? Number(selectedProfileId) : undefined,
            spec_path: uploadRes.spec_path || undefined,
            username: username,
          });
          setLocalLoading(false);
          return;
        }
        throw mappingErr;
      }

      if (!precheck) {
        throw new Error("Mapping precheck did not return a response.");
      }

      const initialOverrides: Record<string, string | null> = {};
      precheck.preview.items.forEach((item) => {
        initialOverrides[item.dp_variable] = item.suggested_column || null;
      });
      setMappingOverrides(initialOverrides);
      setMappingWaivers({});
      setRequiredOverrides({});
      setStatusText("Finalizing mapping review workspace...");
      await new Promise(r => setTimeout(r, 220));
      setMappingReview(precheck);
      setLocalLoading(false);
    } catch (err: any) {
      setErrorText(err.message || "An error occurred during dataset validation.");
      setLocalLoading(false);
    }
  };

  const applyHighConfidenceMatches = () => {
    if (!mappingReview) return;
    const next = { ...mappingOverrides };
    mappingReview.preview.items.forEach(item => {
      if ((item.confidence_band || item.confidence) === "HIGH" && item.suggested_column) {
        next[item.dp_variable] = item.suggested_column;
      }
    });
    setMappingOverrides(next);
  };

  const setManualMapping = (dpVar: string, value: string) => {
    setMappingOverrides({
      ...mappingOverrides,
      [dpVar]: value || null,
    });
  };

  const toggleWaive = (dpVar: string, checked: boolean) => {
    const next = { ...mappingWaivers };
    if (!checked) {
      delete next[dpVar];
    } else {
      next[dpVar] = next[dpVar] || "Approved by reviewer";
    }
    setMappingWaivers(next);
  };

  const setWaiveReason = (dpVar: string, reason: string) => {
    setMappingWaivers({
      ...mappingWaivers,
      [dpVar]: reason,
    });
  };

  const clearMatch = (dpVar: string) => {
    setMappingOverrides({ ...mappingOverrides, [dpVar]: null });
  };

  const getAvailableColumnsFor = (dpVar: string): string[] => {
    const selectedElsewhere = new Set(
      Object.entries(mappingOverrides)
        .filter(([key, value]) => key !== dpVar && Boolean(value))
        .map(([, value]) => String(value))
    );

    return reviewColumns.filter((col) => {
      const currentValue = mappingOverrides[dpVar];
      if (currentValue === col) return true;
      return !selectedElsewhere.has(col);
    });
  };

  const getMatchHelperText = (item: any): string => {
    const selected = (mappingOverrides[item.dp_variable] || "").trim();
    const auto = String(item.auto_match || item.suggested_column || "").trim();
    const band = String(item.confidence_band || item.confidence || "").toUpperCase();

    if (!selected) return "Not mapped";
    if (auto && selected === auto && band === "HIGH") return "✓ Exact Match";

    if (band === "HIGH") return "98% Similarity";
    if (band === "MEDIUM") return "85% Similarity";
    if (band === "LOW") return "70% Similarity";
    return "Manual selection";
  };

  const getIsRequired = (item: any) => {
    const override = requiredOverrides[item.dp_variable];
    return typeof override === "boolean" ? override : Boolean(item.required);
  };

  const setRequiredValue = (dpVar: string, value: boolean) => {
    setRequiredOverrides({
      ...requiredOverrides,
      [dpVar]: value,
    });
  };

  const handleRunWithConfirmedMapping = async () => {
    if (!mappingReview) return;
    setLocalLoading(true);
    setErrorText(null);
    setPipelineStep(4);

    try {
      await api.confirmMapping({
        mapping_id: mappingReview.mapping_id,
        overrides: mappingOverrides,
        waivers: mappingWaivers,
        required_overrides: requiredOverrides,
        block_on_required_unresolved: true,
        manually_added_variables: manuallyAddedVariables,
      });

      setStatusText("Analyzing binary coding variations (0/1, 1/2, Y/N, Yes/No)...");
      await new Promise(r => setTimeout(r, 650));

      setStatusText("Calculating quality score and compiling deductions...");
      await new Promise(r => setTimeout(r, 400));

      await runValidation({
        dataset_path: mappingReview.dataset_path,
        mapping_id: mappingReview.mapping_id,
        username: username
      });
      clearMappingState();
    } catch (err: any) {
      if (typeof err?.message === "string" && err.message.includes("Required DP variables")) {
        setErrorText("Required DP variables are still unresolved. Resolve or waive them before continuing.");
      } else {
        setErrorText(err.message || "An error occurred during dataset validation.");
      }
      setLocalLoading(false);
    }
  };

  const stepsList = [
    { num: 1, text: "Upload and verify file integrity" },
    { num: 2, text: "Parse schema properties and column counts" },
    { num: 3, text: "Match metadata configurations against checklists" },
    { num: 4, text: "Prepare DP-to-dataset mapping suggestions" },
    { num: 5, text: "Finalize mapping review and quality handoff" }
  ];

  const reviewColumns = mappingReview
    ? Array.from(
        new Set([
          ...(mappingReview.dataset_candidates || []).map(c => c.name),
          ...mappingReview.preview.unused_dataset_columns,
          ...mappingReview.preview.items.map(i => i.suggested_column).filter(Boolean) as string[]
        ])
      ).sort((a, b) => a.localeCompare(b))
    : [];

  const resolvedStatus = (item: any) => {
    const selected = mappingOverrides[item.dp_variable];
    const waived = Boolean(mappingWaivers[item.dp_variable]);
    if (selected) return "MATCHED";
    if (waived) return "WAIVED";
    return "UNMATCHED";
  };

  const filteredItems = mappingReview
    ? [
        ...mappingReview.preview.items,
        ...manuallyAddedVariables.map(v => ({
          dp_variable: v.dp_variable,
          required: v.required,
          auto_match: null,
          suggested_column: v.mapped_column || null,
          confidence_band: "MANUAL",
          confidence: "MANUAL",
          status: "MANUAL_ADD",
        }))
      ].filter(item => {
        const status = resolvedStatus(item);
        const confidence = item.confidence_band || item.confidence;
        const search = mappingSearch.trim().toLowerCase();
        if (search) {
          const selected = (mappingOverrides[item.dp_variable] || "").toLowerCase();
          const auto = (item.auto_match || item.suggested_column || "").toLowerCase();
          const dp = item.dp_variable.toLowerCase();
          if (!dp.includes(search) && !selected.includes(search) && !auto.includes(search)) return false;
        }
        if (requiredOnly && !getIsRequired(item)) return false;
        if (unmatchedOnly && status !== "UNMATCHED") return false;
        if (lowConfidenceOnly && !(confidence === "LOW" || confidence === "NONE")) return false;
        return true;
      })
    : [];

  const unresolvedRequiredCount = mappingReview
    ? [
        ...mappingReview.preview.items,
        ...manuallyAddedVariables
      ].filter(item => getIsRequired(item) && resolvedStatus(item) === "UNMATCHED").length
    : 0;

  const unmatchedItems = mappingReview
    ? [
        ...mappingReview.preview.items,
        ...manuallyAddedVariables
      ].filter(item => resolvedStatus(item) === "UNMATCHED")
    : [];

  const canContinue = mappingReview ? unresolvedRequiredCount === 0 : false;
  const progressPercent = Math.min(100, Math.max(0, Math.round((pipelineStep / 5) * 100)));

  return (
    <div className={`${mappingReview ? "max-w-6xl" : "max-w-3xl"} mx-auto space-y-8 animate-apple-fade`}>
      {/* Apple-style Page Header */}
      <div className="border-b border-neutral-900 pb-5">
        <h1 className="text-3xl font-semibold tracking-tight text-white">
          Ingestion Hub
        </h1>
        <p className="text-sm text-neutral-500 mt-1">Upload stacked SAV datasets and link tracking profiles or specifications.</p>
      </div>

      <div className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl relative overflow-hidden">
        {localLoading ? (
          /* Sequential Pipeline Tracker - Apple style */
          <div className="py-12 space-y-8 max-w-2xl mx-auto">
            <div className="text-center space-y-3">
              <h2 className="text-2xl font-semibold tracking-tight text-white">Validating Dataset</h2>
              <p className="text-sm text-neutral-500">Processing checks offline in the local compiler engine.</p>
            </div>

            <div className="space-y-3 pt-6">
              {stepsList.map(step => {
                const isActive = pipelineStep === step.num;
                const isCompleted = pipelineStep > step.num;
                return (
                  <div key={step.num} className="flex items-start gap-3 text-sm">
                    <div className="flex items-center justify-center shrink-0 mt-0.5">
                      {isCompleted ? (
                        <div className="h-6 w-6 rounded-full bg-emerald-500/15 border border-emerald-500/40 flex items-center justify-center">
                          <Check className="h-3.5 w-3.5 text-emerald-400 stroke-[2.5]" />
                        </div>
                      ) : isActive ? (
                        <div className="h-6 w-6 rounded-full border-2 border-white/40 flex items-center justify-center">
                          <span className="h-2.5 w-2.5 rounded-full bg-white animate-pulse"></span>
                        </div>
                      ) : (
                        <div className="h-6 w-6 rounded-full border border-neutral-700 flex items-center justify-center text-xs text-neutral-500 font-medium font-mono">
                          {step.num}
                        </div>
                      )}
                    </div>
                    <span className={`transition-all duration-200 leading-relaxed ${
                      isCompleted ? "text-neutral-500 line-through decoration-neutral-800/50" : isActive ? "text-white font-medium" : "text-neutral-600"
                    }`}>
                      {step.text}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="pt-8">
              <div className="flex items-center justify-between mb-2">
                <div className="text-[11px] font-semibold tracking-[0.12em] uppercase text-neutral-500 dark:text-neutral-500">
                  Progress
                </div>
                <div className="text-[11px] font-semibold px-2 py-1 rounded-md bg-neutral-100 text-neutral-700 border border-neutral-200 dark:bg-white/5 dark:text-neutral-300 dark:border-white/10">
                  {progressPercent}%
                </div>
              </div>
              <div className="relative h-2.5 w-full rounded-full bg-neutral-100 border border-neutral-200 overflow-hidden dark:bg-neutral-900/70 dark:border-neutral-700/70">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out bg-gradient-to-r from-blue-500 via-sky-500 to-cyan-400 dark:from-white dark:via-slate-100 dark:to-white shadow-[0_0_16px_rgba(56,189,248,0.45)] dark:shadow-[0_0_18px_rgba(255,255,255,0.35)]"
                  style={{ width: `${progressPercent}%` }}
                ></div>
                <div
                  className="absolute top-0 h-full w-20 bg-gradient-to-r from-transparent via-white/35 to-transparent dark:via-white/25 pointer-events-none"
                  style={{ left: `calc(${progressPercent}% - 40px)` }}
                ></div>
              </div>
            </div>
          </div>
        ) : mappingReview ? (
          <div className="space-y-4">
            <div className="border border-neutral-900 rounded-2xl p-4 bg-neutral-950">
              <h3 className="text-base font-semibold text-white">Manual Mapping Review</h3>
              <p className="text-xs text-neutral-500 mt-1">Calm, compact review before validation run.</p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 mt-4 text-xs">
                <div className="mapping-kpi">DP Variables <span className="mapping-kpi-value">{mappingReview.preview.summary.dp_variables}</span></div>
                <div className="mapping-kpi">Matched <span className="mapping-kpi-value">{mappingReview.preview.summary.matched}</span></div>
                <div className="mapping-kpi">Unmatched Required <span className="mapping-kpi-value">{unresolvedRequiredCount}</span></div>
                <div className="mapping-kpi">Unused Columns <span className="mapping-kpi-value">{mappingReview.preview.summary.unused_dataset_columns}</span></div>
              </div>
            </div>

            {unresolvedRequiredCount > 0 && (
              <div className="mapping-impact-warning">
                Estimated impact: <span className="mapping-impact-value">{unresolvedRequiredCount}</span> required variables unresolved.
              </div>
            )}
            {unresolvedRequiredCount === 0 && (
              <div className="mapping-impact-success">
                ✓ All required variables resolved. Ready for validation.
              </div>
            )}

            <div className="mb-3 flex gap-3 items-center">
              <button type="button" onClick={applyHighConfidenceMatches} className="mapping-btn-accept">
                Accept High Confidence Matches
              </button>
              <button type="button" onClick={() => setShowAddVariableForm(!showAddVariableForm)} className="mapping-btn-accept" style={{backgroundColor: 'var(--primary-color, #3b82f6)'}}>
                <Plus className="h-4 w-4 inline mr-1" /> Add Missing Variable
              </button>
            </div>

            {showAddVariableForm && (
              <div className="border border-white/8 rounded-lg p-5 bg-gradient-to-br from-white/[0.05] via-white/[0.02] to-transparent backdrop-blur-xl shadow-lg shadow-black/30">
                <div className="flex items-center gap-3.5">
                  <div className="flex-1 min-w-0">
                    <input
                      type="text"
                      value={addVarName}
                      onChange={(e) => setAddVarName(e.target.value)}
                      placeholder="Variable name"
                      className="apple-input w-full text-sm py-2.5"
                    />
                  </div>
                  
                  <label className="inline-flex items-center gap-2.5 text-neutral-400 shrink-0">
                    <input
                      type="checkbox"
                      checked={addVarRequired}
                      onChange={(e) => setAddVarRequired(e.target.checked)}
                      className="w-4 h-4 rounded cursor-pointer accent-white/60"
                    />
                    <span className="text-xs font-medium tracking-tight">Required</span>
                  </label>

                  <button
                    type="button"
                    onClick={() => {
                      if (addVarName.trim()) {
                        addManualVariable({
                          dp_variable: addVarName.trim(),
                          required: addVarRequired,
                        });
                        setAddVarName("");
                        setAddVarRequired(false);
                      }
                    }}
                    className="shrink-0 px-5 py-2.5 bg-white text-black text-xs font-semibold rounded-lg hover:bg-white/95 hover:shadow-lg hover:shadow-white/10 transition-all duration-200"
                  >
                    Add
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setShowAddVariableForm(false);
                      setAddVarName("");
                      setAddVarRequired(false);
                    }}
                    className="shrink-0 px-4 py-2.5 text-neutral-500 text-xs font-medium hover:text-neutral-200 transition-colors duration-200"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {manuallyAddedVariables.length > 0 && (
              <div className="border border-neutral-200 dark:border-white/8 rounded-lg p-4 bg-neutral-50 dark:bg-gradient-to-br dark:from-white/[0.04] dark:to-transparent dark:backdrop-blur-lg">
                <h4 className="text-xs font-semibold text-neutral-900 dark:text-white/90 mb-3 tracking-tight uppercase">Added Variables</h4>
                <div className="space-y-2">
                  {manuallyAddedVariables.map((v, idx) => (
                    <div key={`manual-${idx}`} className="group flex items-center justify-between px-4 py-3 bg-white dark:bg-gradient-to-r border border-neutral-200 dark:border-white/10 hover:border-neutral-300 dark:hover:border-white/20 from-white/[0.04] to-white/[0.01] dark:hover:from-white/[0.08] dark:hover:to-white/[0.03] rounded-lg transition-all duration-200 shadow-sm hover:shadow-md dark:shadow-sm dark:hover:shadow-md">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="flex-shrink-0 w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-400 dark:to-blue-500"></div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-neutral-900 dark:text-white/95 truncate">{v.dp_variable}</p>
                          {v.required && (
                            <span className="inline-flex items-center gap-1.5 mt-1 px-2.5 py-1 text-[11px] font-semibold text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-gradient-to-r dark:from-amber-500/15 dark:to-amber-600/10 border border-amber-300 dark:border-amber-500/30 rounded-md">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-600 dark:bg-amber-400"></span>
                              REQUIRED
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeManualVariable(idx)}
                        className="flex-shrink-0 ml-2 p-1.5 text-neutral-400 dark:text-neutral-500 hover:text-rose-500 dark:hover:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-500/10 rounded-md transition-all duration-150 group-hover:opacity-100"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mapping-toolbar">
              <input
                value={mappingSearch}
                onChange={(e) => setMappingSearch(e.target.value)}
                placeholder="Search DP variable or mapped column"
                className="mapping-search"
              />
              <div className="mapping-filter-group">
                <button type="button" onClick={() => setRequiredOnly(!requiredOnly)} className={`mapping-pill ${requiredOnly ? "is-on" : ""}`}>Required</button>
                <button type="button" onClick={() => setUnmatchedOnly(!unmatchedOnly)} className={`mapping-pill ${unmatchedOnly ? "is-on" : ""}`}>Unmatched</button>
                <button type="button" onClick={() => setLowConfidenceOnly(!lowConfidenceOnly)} className={`mapping-pill ${lowConfidenceOnly ? "is-on" : ""}`}>Low Confidence</button>
              </div>
            </div>

            <div className="border border-neutral-900 rounded-xl overflow-hidden">
              <div className="overflow-auto max-h-[440px]">
                <table className="w-full min-w-[900px] table-fixed text-left apple-table mapping-table">
                  <colgroup>
                    <col style={{ width: "28%" }} />
                    <col style={{ width: "29%" }} />
                    <col style={{ width: "12%" }} />
                    <col style={{ width: "10%" }} />
                    <col style={{ width: "10%" }} />
                    <col style={{ width: "11%" }} />
                  </colgroup>
                <thead>
                  <tr>
                    <th className="py-2.5 px-3 text-neutral-500 text-xs whitespace-nowrap">DP Variable</th>
                    <th className="py-2.5 px-3 text-neutral-500 text-xs whitespace-nowrap">Mapped Column</th>
                    <th className="py-2.5 px-3 text-neutral-500 text-xs whitespace-nowrap">Status</th>
                    <th className="py-2.5 px-3 text-neutral-500 text-xs whitespace-nowrap">Confidence</th>
                    <th className="py-2.5 px-3 text-neutral-500 text-xs whitespace-nowrap">Required</th>
                    <th className="py-2.5 px-3 text-neutral-500 text-xs text-center">Waive (Optional)</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map((item, idx) => (
                    <tr key={`${item.dp_variable}-${idx}`}>
                      <td className="py-1.5 px-3 text-xs font-mono text-neutral-900 dark:text-white truncate" title={item.dp_variable}>{item.dp_variable}</td>
                      <td className="py-1.5 px-3">
                        <input
                          list={`mapping-cols-${idx}`}
                          value={mappingOverrides[item.dp_variable] || ""}
                          onChange={(e) => setManualMapping(item.dp_variable, e.target.value)}
                          placeholder="Type to search columns"
                          className="apple-select mapping-primary-input w-full"
                        />
                        <datalist id={`mapping-cols-${idx}`}>
                          {getAvailableColumnsFor(item.dp_variable).map(col => (
                            <option key={col} value={col}>{col}</option>
                          ))}
                        </datalist>
                        <div className="mt-1 flex items-center justify-between gap-2 mapping-match-meta">
                          <span className="text-[10px] text-neutral-500 dark:text-neutral-400 leading-none">{getMatchHelperText(item)}</span>
                          <button type="button" onClick={() => clearMatch(item.dp_variable)} className="mapping-clear-action text-[10px] text-neutral-500 hover:text-red-600 dark:hover:text-red-400 leading-none transition-colors">
                            Clear
                          </button>
                        </div>
                      </td>
                      <td className="py-1.5 px-3 text-xs">
                        <span className={`mapping-status-pill ${resolvedStatus(item) === "MATCHED" ? "is-matched" : resolvedStatus(item) === "WAIVED" ? "is-waived" : "is-unmatched"}`}>
                          {resolvedStatus(item)}
                        </span>
                      </td>
                      <td className="py-1.5 px-3 text-xs">
                        <span className={`mapping-confidence-pill ${(item.confidence_band || item.confidence) === "HIGH" ? "is-high" : (item.confidence_band || item.confidence) === "MEDIUM" ? "is-medium" : (item.confidence_band || item.confidence) === "LOW" ? "is-low" : "is-none"}`}>
                          {item.confidence_band || item.confidence}
                        </span>
                      </td>
                      <td className="py-1.5 px-3 text-xs text-neutral-700 dark:text-neutral-300">
                        <select
                          value={getIsRequired(item) ? "yes" : "no"}
                          onChange={(e) => setRequiredValue(item.dp_variable, e.target.value === "yes")}
                          className="apple-select mapping-required-select w-full"
                        >
                          <option value="yes">Yes</option>
                          <option value="no">No</option>
                        </select>
                      </td>
                      <td className="py-1.5 px-3 text-xs text-center">
                        <div className="relative inline-flex items-center justify-center group/waive">
                          <label className={`inline-flex items-center justify-center text-neutral-700 dark:text-neutral-300 ${getIsRequired(item) ? "cursor-not-allowed opacity-75" : ""}`}>
                            <input
                              type="checkbox"
                              checked={Boolean(mappingWaivers[item.dp_variable])}
                              disabled={getIsRequired(item)}
                              onChange={(e) => toggleWaive(item.dp_variable, e.target.checked)}
                              className={getIsRequired(item) ? "cursor-not-allowed" : ""}
                            />
                          </label>
                          {getIsRequired(item) && (
                            <div className="pointer-events-none absolute right-0 top-full mt-1 z-20 whitespace-nowrap rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-2 py-1 text-[10px] text-neutral-700 dark:text-neutral-300 opacity-0 translate-y-1 transition-all duration-150 group-hover/waive:opacity-100 group-hover/waive:translate-y-0 shadow-md">
                              Required variables cannot be waived.
                            </div>
                          )}
                        </div>
                        {Boolean(mappingWaivers[item.dp_variable]) && (
                          <input
                            value={mappingWaivers[item.dp_variable] || ""}
                            onChange={(e) => setWaiveReason(item.dp_variable, e.target.value)}
                            className="apple-input w-full mt-1.5 text-xs"
                            placeholder="Waive reason"
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
                </table>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-3">
              <div className="border border-neutral-900 rounded-xl p-4">
                <h4 className="text-xs text-neutral-400 mb-2">Unmatched Variables</h4>
                <div className="max-h-40 overflow-auto space-y-1 text-xs">
                  {unmatchedItems.length === 0 && <p className="text-neutral-500">No unmatched variables.</p>}
                  {unmatchedItems.map(item => (
                    <div key={`unmatched-${item.dp_variable}`} className="font-mono text-neutral-300">
                      {item.dp_variable} {item.required ? "(Required)" : "(Optional)"}
                    </div>
                  ))}
                </div>
              </div>

              <div className="border border-neutral-900 rounded-xl p-4">
                <h4 className="text-xs text-neutral-400 mb-2">Unused Dataset Columns</h4>
                <div className="max-h-40 overflow-auto space-y-1 text-xs">
                  {(mappingReview.preview.unused_dataset_candidates || []).length === 0 && <p className="text-neutral-500">No unused columns.</p>}
                  {(mappingReview.preview.unused_dataset_candidates || []).map(col => (
                    <div key={`unused-${col.name}`} className="text-neutral-300 font-mono">
                      {col.name} <span className="text-neutral-500">[{col.type_hint}]</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {errorText && (
              <div className="p-4 bg-rose-950/20 border border-rose-900/20 text-rose-400 text-xs rounded-xl flex items-start gap-3">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <p className="leading-relaxed font-medium">{errorText}</p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => clearMappingState()}
                className="apple-btn-secondary px-4 py-2"
              >
                Back to Upload
              </button>
              <button
                type="button"
                onClick={handleRunWithConfirmedMapping}
                disabled={!canContinue}
                className="apple-btn-primary flex-1 py-3.5 uppercase tracking-wider font-semibold disabled:opacity-40"
              >
                <Play className="h-3.5 w-3.5 fill-black" /> Confirm Mapping & Run Validation
              </button>
            </div>
          </div>
        ) : (
          /* Upload Form */
          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Input Options row */}
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-2 flex flex-col">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-450">
                  Validation Profile Template
                </label>
                <select
                  value={selectedProfileId}
                  onChange={(e) => setSelectedProfileId(e.target.value)}
                  className="apple-select w-full"
                >
                  <option value="">-- Ad-hoc (Direct Spec Upload) --</option>
                  {profiles.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2 flex flex-col">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-450">
                  Operator Signature
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="apple-input w-full"
                  placeholder="e.g. DP Analyst"
                />
              </div>
            </div>

            {/* Upload Dropzones */}
            <div className="grid gap-6 md:grid-cols-2 items-stretch">
              {/* Spec Sheet Upload */}
              <div className="space-y-2 flex flex-col">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-450 min-h-[18px] leading-none flex items-center">
                  1. DP Specification Sheet (Optional)
                </label>

                {specFile ? (
                  <div className="border border-neutral-200 dark:border-neutral-800 rounded-xl p-4 bg-white dark:bg-neutral-900/40 shadow-sm dark:shadow-none flex items-center gap-3 min-h-[88px] flex-1">
                    <div className="p-2 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 shrink-0 self-center">
                        <File className="h-5 w-5 text-neutral-700 dark:text-white" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-neutral-900 dark:text-white truncate leading-tight">{specFile.name}</p>
                        <p className="text-[10px] text-neutral-500 dark:text-neutral-550 font-mono">{(specFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSpecFile(null)}
                      className="text-[10px] font-medium text-neutral-700 dark:text-neutral-500 hover:text-red-600 dark:hover:text-red-400 transition-colors px-2.5 py-1 bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-md shrink-0 self-center"
                    >
                      Clear
                    </button>
                  </div>
                ) : (
                  <div className="relative border border-dashed rounded-xl p-8 transition-all duration-200 flex flex-col items-center justify-center text-center cursor-pointer min-h-[160px] group apple-dropzone flex-1">
                    <input
                      type="file"
                      onChange={handleSpecChange}
                      accept=".xlsx,.csv"
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <UploadCloud className="h-7 w-7 mb-3" />
                    <div>
                      <p className="text-xs font-semibold">Choose specification template</p>
                      <p className="text-[10px] mt-1">Excel (.xlsx) or CSV specs</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Dataset Upload */}
              <div className="space-y-2 flex flex-col">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-450 min-h-[18px] leading-none flex items-center gap-1.5">
                  2. Target Dataset <span className="text-rose-500">*</span>
                </label>

                {datasetFile ? (
                  <div className="border border-neutral-200 dark:border-neutral-800 rounded-xl p-4 bg-white dark:bg-neutral-900/40 shadow-sm dark:shadow-none flex items-center gap-3 min-h-[88px] flex-1">
                    <div className="p-2 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 shrink-0 self-center">
                        <File className="h-5 w-5 text-neutral-700 dark:text-white" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-neutral-900 dark:text-white truncate leading-tight">{datasetFile.name}</p>
                        <p className="text-[10px] text-neutral-500 dark:text-neutral-550 font-mono">{(datasetFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setDatasetFile(null)}
                      className="text-[10px] font-medium text-neutral-700 dark:text-neutral-500 hover:text-red-600 dark:hover:text-red-400 transition-colors px-2.5 py-1 bg-neutral-100 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-md shrink-0 self-center"
                    >
                      Clear
                    </button>
                  </div>
                ) : (
                  <div className="relative border border-dashed rounded-xl p-8 transition-all duration-200 flex flex-col items-center justify-center text-center cursor-pointer min-h-[160px] group apple-dropzone flex-1">
                    <input
                      type="file"
                      onChange={handleDatasetChange}
                      accept=".sav,.xlsx,.xls,.csv"
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <UploadCloud className="h-7 w-7 mb-3" />
                    <div>
                      <p className="text-xs font-semibold">Choose stacked dataset file</p>
                      <p className="text-[10px] mt-1">SPSS (.sav), Excel (.xlsx), or CSV</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Error Notification banner */}
            {errorText && (
              <div className="p-4 bg-rose-950/20 border border-rose-900/20 text-rose-400 text-xs rounded-xl flex items-start gap-3">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <p className="leading-relaxed font-medium">{errorText}</p>
              </div>
            )}

            {/* Action submit button */}
            <button
              type="submit"
              className="apple-btn-primary w-full py-3.5 uppercase tracking-wider font-semibold"
            >
              <Play className="h-3.5 w-3.5 fill-black" /> Run Quality Validation 
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
