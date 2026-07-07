const API_BASE = "/api/v1";
const API_FALLBACK_ORIGIN = "http://127.0.0.1:8000";

const toFallbackUrl = (url: string): string => {
  if (/^https?:\/\//i.test(url)) return url;
  return `${API_FALLBACK_ORIGIN}${url}`;
};

const apiFetch = async (url: string, init?: RequestInit): Promise<Response> => {
  const primary = await fetch(url, init);
  if (primary.status !== 404 || /^https?:\/\//i.test(url)) {
    return primary;
  }
  // Fallback for environments where frontend proxy is not active.
  return fetch(toFallbackUrl(url), init);
};

const readErrorDetail = async (res: Response, fallback: string): Promise<string> => {
  try {
    const err = await res.json();
    if (typeof err?.detail === "string") return err.detail;
    if (err?.detail?.message) return err.detail.message;
  } catch {
    // ignore JSON parse errors and return fallback
  }
  return fallback;
};

export interface ProjectProfile {
  id: number;
  name: string;
  description?: string;
  config: {
    variables: Array<{
      name: string;
      label?: string;
      category: string;
      required: boolean;
      data_type: string;
      is_binary: boolean;
      expected_values?: any[];
      value_labels?: Record<string, string>;
    }>;
  };
}

export interface AuditLog {
  id: number;
  dataset_name: string;
  profile_name: string;
  upload_timestamp: string;
  validation_timestamp: string;
  username: string;
  result: "PASS" | "WARNING" | "FAIL";
  score: number;
  report_xlsx_path?: string;
  report_pdf_path?: string;
  report_json_path?: string;
  summary_data?: {
    rows: number;
    columns: number;
    coverage_pct: number;
    missing_vars: number;
    binary_warnings: number;
    binary_fails: number;
    null_red_count: number;
  };
}

export interface MappingPreviewItem {
  dp_variable: string;
  normalized_label?: string;
  required: boolean;
  category: string;
  suggested_column?: string | null;
  auto_match?: string | null;
  auto_reason?: string;
  dataset_type_hint?: string;
  candidates?: Array<{ column: string; score: number; reason: string; type_hint: string }>;
  confidence_score: number;
  confidence: "HIGH" | "MEDIUM" | "LOW" | "NONE";
  confidence_band?: "HIGH" | "MEDIUM" | "LOW" | "NONE";
  status: "MATCHED" | "UNMATCHED";
}

export interface MappingPrecheckResponse {
  mapping_id: string;
  dataset_path: string;
  preview: {
    items: MappingPreviewItem[];
    summary: {
      dp_variables: number;
      dataset_columns: number;
      matched: number;
      unmatched_required: number;
      unmatched_optional: number;
      unused_dataset_columns: number;
    };
    unmatched_required: MappingPreviewItem[];
    unmatched_optional: MappingPreviewItem[];
    unused_dataset_columns: string[];
    unused_dataset_candidates?: Array<{ name: string; type_hint: string }>;
  };
  suggested_mapping: Record<string, string>;
  waivers?: Record<string, string>;
  summary?: {
    total_dp_variables: number;
    auto_matched: number;
    manually_mapped: number;
    waived: number;
    unresolved: number;
    unresolved_required: number;
  };
  mapping_diagnostics?: {
    unresolved_required: string[];
    unresolved_optional: string[];
    mismatch_diagnostics?: any[];
  };
  dataset_candidates?: Array<{ name: string; type_hint: string }>;
}

export const api = {
  // Profiles
  async getProfiles(): Promise<ProjectProfile[]> {
    const res = await apiFetch(`${API_BASE}/project-profile`);
    if (!res.ok) throw new Error("Failed to load project profiles");
    return res.json();
  },

  async createProfile(profile: Omit<ProjectProfile, "id">): Promise<ProjectProfile> {
    const res = await apiFetch(`${API_BASE}/project-profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create project profile");
    }
    return res.json();
  },

  async deleteProfile(id: number): Promise<void> {
    const res = await apiFetch(`${API_BASE}/project-profile/${id}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error("Failed to delete project profile");
  },

  // File Uploads
  async uploadFiles(datasetFile: File, specFile?: File): Promise<{
    dataset_filename: string;
    dataset_path: string;
    spec_filename?: string;
    spec_path?: string;
  }> {
    const formData = new FormData();
    formData.append("dataset", datasetFile);
    if (specFile) {
      formData.append("spec", specFile);
    }

    const res = await apiFetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error(await readErrorDetail(res, "Failed to upload files"));
    return res.json();
  },

  // Validate
  async validate(payload: {
    dataset_path: string;
    profile_id?: number;
    spec_path?: string;
    mapping_id?: string;
    username?: string;
  }): Promise<any> {
    const formData = new FormData();
    formData.append("dataset_path", payload.dataset_path);
    if (payload.profile_id) formData.append("profile_id", String(payload.profile_id));
    if (payload.spec_path) formData.append("spec_path", payload.spec_path);
    if (payload.mapping_id) formData.append("mapping_id", payload.mapping_id);
    if (payload.username) formData.append("username", payload.username);

    const res = await apiFetch(`${API_BASE}/validate`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      throw new Error(await readErrorDetail(res, "Validation execution failed"));
    }
    return res.json();
  },

  async precheckMapping(payload: {
    dataset_path: string;
    profile_id?: number;
    spec_path?: string;
  }): Promise<MappingPrecheckResponse> {
    const formData = new FormData();
    formData.append("dataset_path", payload.dataset_path);
    if (payload.profile_id) formData.append("profile_id", String(payload.profile_id));
    if (payload.spec_path) formData.append("spec_path", payload.spec_path);

    const res = await apiFetch(`${API_BASE}/precheck-mapping`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      throw new Error(await readErrorDetail(res, "Failed to run mapping precheck"));
    }
    return res.json();
  },

  async confirmMapping(payload: {
    mapping_id: string;
    overrides: Record<string, string | null>;
    waivers?: Record<string, string>;
    required_overrides?: Record<string, boolean>;
    block_on_required_unresolved?: boolean;
    manually_added_variables?: Array<{ dp_variable: string; required: boolean }>;
  }): Promise<{
    mapping_id: string;
    confirmed_mapping: Record<string, string>;
    waivers: Record<string, string>;
    summary: Record<string, number>;
    mapping_diagnostics: {
      unresolved_required: string[];
      unresolved_optional: string[];
      mismatch_diagnostics?: any[];
    };
  }> {
    const res = await apiFetch(`${API_BASE}/confirm-mapping`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      throw new Error(await readErrorDetail(res, "Failed to confirm mapping"));
    }
    return res.json();
  },

  // History / Auditing
  async getHistory(): Promise<AuditLog[]> {
    const res = await apiFetch(`${API_BASE}/validation-history`);
    if (!res.ok) throw new Error("Failed to retrieve validation history");
    return res.json();
  },

  async getReportById(id: number): Promise<any> {
    const res = await apiFetch(`${API_BASE}/report/${id}`);
    if (!res.ok) throw new Error("Failed to load report detail");
    return res.json();
  }
};
