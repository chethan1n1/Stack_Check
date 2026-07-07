import { useState, useEffect } from "react";
import { useAppStore } from "../store/useAppStore";
import { Layers, Plus, Trash2, CheckCircle2, FileSpreadsheet, UploadCloud, AlertCircle, X } from "lucide-react";

export default function Profiles() {
  const { profiles, loadProfiles, deleteProfile } = useAppStore();
  const [showAddModal, setShowAddModal] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [profileDesc, setProfileDesc] = useState("");
  
  const [specFile, setSpecFile] = useState<File | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [successText, setSuccessText] = useState<string | null>(null);

  useEffect(() => {
    loadProfiles();
  }, []);

  const handleSpecUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSpecFile(e.target.files[0]);
    }
  };

  return (
    <>
      <div className="space-y-10 animate-apple-fade">
      
      {/* Page Header */}
      <div className="flex justify-between items-center border-b border-neutral-900 pb-5">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-white">Tracking Profiles</h1>
          <p className="text-sm text-neutral-500 mt-1">Configure reusable dictionary templates for tracking waves.</p>
        </div>
        
        <button
          onClick={() => {
            setShowAddModal(true);
            setErrorText(null);
            setSuccessText(null);
            setProfileName("");
            setProfileDesc("");
            setSpecFile(null);
          }}
          className="apple-btn-primary"
        >
          <Plus className="h-4 w-4" /> Create Profile
        </button>
      </div>

      {/* Grid of Profiles */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {profiles.map(profile => (
          <div key={profile.id} className="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl flex flex-col justify-between space-y-4 hover:border-neutral-800 transition-colors duration-250">
            <div className="space-y-2">
              <div className="flex justify-between items-start">
                <h3 className="font-semibold text-sm text-white truncate pr-4">{profile.name}</h3>
                <Layers className="h-4.5 w-4.5 text-neutral-500 shrink-0" />
              </div>
              <p className="text-xs text-neutral-500 line-clamp-3 leading-relaxed">{profile.description || "No description provided."}</p>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-neutral-900">
              <span className="text-[10px] font-mono text-neutral-450 uppercase tracking-wide">
                {profile.config.variables.length} expected variables
              </span>
              <button
                onClick={() => {
                  if (confirm(`Are you sure you want to delete profile "${profile.name}"?`)) {
                    deleteProfile(profile.id);
                  }
                }}
                className="text-neutral-550 hover:text-rose-500 transition-colors p-1"
                title="Delete Profile Template"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}

        {profiles.length === 0 && (
          <div className="border border-dashed border-neutral-850 p-12 rounded-2xl text-center sm:col-span-3 text-neutral-500 text-xs">
            No profile templates registered. Create a profile to save expected variables list.
          </div>
        )}
      </div>

      </div>

      {/* Add Profile Modal - macOS/iOS styled overlay */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-md">
          <div className="bg-neutral-950 border border-neutral-900 w-full max-w-md rounded-2xl p-6 space-y-6 shadow-2xl relative animate-apple-fade">
            
            <div className="flex justify-between items-center border-b border-neutral-900 pb-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-neutral-450" /> Register Profile Template
              </h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-neutral-500 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Notifications */}
            {errorText && (
              <div className="p-3.5 bg-rose-950/20 border border-rose-900/20 text-rose-400 text-xs rounded-xl flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <p>{errorText}</p>
              </div>
            )}
            {successText && (
              <div className="p-3.5 bg-emerald-950/20 border border-emerald-900/20 text-emerald-450 text-xs rounded-xl flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <p>{successText}</p>
              </div>
            )}

            <div className="space-y-4">
              <div className="space-y-1.5 flex flex-col">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-450">
                  Profile Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  className="apple-input w-full"
                  placeholder="e.g. Wave Track Survey"
                />
              </div>

              <div className="space-y-1.5 flex flex-col">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-450">
                  Description
                </label>
                <textarea
                  value={profileDesc}
                  onChange={(e) => setProfileDesc(e.target.value)}
                  className="apple-input w-full h-20 resize-none"
                  placeholder="e.g. Expected variable structures and validations for quarterly waves."
                />
              </div>

              {/* Upload Dropzone */}
              <div className="space-y-1.5 flex flex-col">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-neutral-450">
                  DP Specification Sheet <span className="text-rose-500">*</span>
                </label>
                
                {specFile ? (
                  <div className="border border-neutral-800 rounded-xl p-3 bg-neutral-900/40 flex items-center justify-between">
                    <span className="text-xs text-neutral-200 truncate max-w-[200px] font-mono">{specFile.name}</span>
                    <button 
                      type="button" 
                      onClick={() => setSpecFile(null)}
                      className="text-[10px] font-medium text-neutral-500 hover:text-white"
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <div className="relative border border-dashed rounded-xl p-4 text-center cursor-pointer flex flex-col items-center justify-center min-h-[90px] group apple-dropzone">
                    <input
                      type="file"
                      onChange={handleSpecUpload}
                      accept=".xlsx,.csv"
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <UploadCloud className="h-6 w-6 mb-1.5" />
                    <span className="text-[10px] font-semibold">Upload spec sheet (.xlsx, .csv)</span>
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={async () => {
                if (!profileName.trim()) {
                  setErrorText("Please provide a template profile name.");
                  return;
                }
                if (!specFile) {
                  setErrorText("Please attach the tracking specifications sheet file.");
                  return;
                }

                setErrorText(null);
                setSuccessText(null);

                try {
                  const formData = new FormData();
                  formData.append("name", profileName);
                  formData.append("description", profileDesc);
                  formData.append("spec", specFile);

                  const res = await fetch("/api/v1/project-profile/upload-spec", {
                    method: "POST",
                    body: formData
                  });

                  if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Upload compilation failed.");
                  }

                  setSuccessText("Template registered successfully!");
                  setProfileName("");
                  setProfileDesc("");
                  setSpecFile(null);
                  loadProfiles();
                  setTimeout(() => setShowAddModal(false), 800);
                } catch (err: any) {
                  setErrorText(err.message);
                }
              }}
              className="apple-btn-primary w-full py-2.5 uppercase tracking-wider font-semibold text-xs"
            >
              Confirm Registration
            </button>
          </div>
        </div>
      )}
    </>
  );
}
