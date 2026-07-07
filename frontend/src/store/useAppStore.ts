import { create } from "zustand";
import { api, ProjectProfile, AuditLog, MappingPrecheckResponse } from "../services/api";

interface ManuallyAddedVariable {
  dp_variable: string;
  required: boolean;
  mapped_column?: string;
}

interface AppState {
  activePage: string;
  profiles: ProjectProfile[];
  history: AuditLog[];
  activeReport: any | null;
  mappingReview: MappingPrecheckResponse | null;
  mappingOverrides: Record<string, string | null>;
  mappingWaivers: Record<string, string>;
  manuallyAddedVariables: ManuallyAddedVariable[];
  loading: boolean;
  error: string | null;
  
  setActivePage: (page: string) => void;
  setActiveReport: (report: any | null) => void;
  setMappingReview: (review: MappingPrecheckResponse | null) => void;
  setMappingOverrides: (overrides: Record<string, string | null>) => void;
  setMappingWaivers: (waivers: Record<string, string>) => void;
  addManualVariable: (variable: ManuallyAddedVariable) => void;
  removeManualVariable: (index: number) => void;
  clearMappingState: () => void;
  loadProfiles: () => Promise<void>;
  loadHistory: () => Promise<void>;
  createProfile: (profile: Omit<ProjectProfile, "id">) => Promise<void>;
  deleteProfile: (id: number) => Promise<void>;
  runValidation: (payload: { dataset_path: string; profile_id?: number; spec_path?: string; mapping_id?: string; username?: string }) => Promise<any>;
  theme: "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  activePage: "upload",
  profiles: [],
  history: [],
  activeReport: null,
  mappingReview: null,
  mappingOverrides: {},
  mappingWaivers: {},
  manuallyAddedVariables: [],
  loading: false,
  error: null,
  theme: (localStorage.getItem("theme") as "light" | "dark") || "dark",

  setActivePage: (page) => set({ activePage: page }),
  setActiveReport: (report) => set({ activeReport: report }),
  setMappingReview: (review) => set({ mappingReview: review }),
  setMappingOverrides: (overrides) => set({ mappingOverrides: overrides }),
  setMappingWaivers: (waivers) => set({ mappingWaivers: waivers }),
  addManualVariable: (variable) => set((state) => ({
    manuallyAddedVariables: [...state.manuallyAddedVariables, variable],
  })),
  removeManualVariable: (index) => set((state) => ({
    manuallyAddedVariables: state.manuallyAddedVariables.filter((_, i) => i !== index),
  })),
  clearMappingState: () => set({ mappingReview: null, mappingOverrides: {}, mappingWaivers: {}, manuallyAddedVariables: [] }),
  setTheme: (theme) => {
    localStorage.setItem("theme", theme);
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    set({ theme });
  },

  loadProfiles: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.getProfiles();
      set({ profiles: data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  loadHistory: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.getHistory();
      set({ history: data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  createProfile: async (profile) => {
    set({ loading: true, error: null });
    try {
      await api.createProfile(profile);
      await get().loadProfiles();
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  deleteProfile: async (id) => {
    set({ loading: true, error: null });
    try {
      await api.deleteProfile(id);
      await get().loadProfiles();
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  runValidation: async (payload) => {
    set({ loading: true, error: null });
    try {
      const results = await api.validate(payload);
      set({ activeReport: results, activePage: "validation-center", loading: false });
      get().loadHistory();
      return results;
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  }
}));
