import { useEffect, useState } from "react";
import { useAppStore } from "./store/useAppStore";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import ValidationCenter from "./pages/ValidationCenter";
import Profiles from "./pages/Profiles";
import Logs from "./pages/Logs";
import Settings from "./pages/Settings";

import { LayoutDashboard, UploadCloud, ShieldCheck, History, Layers, Settings as SettingsIcon, Database, Sun, Moon, ChevronsLeft, ChevronsRight } from "lucide-react";

export default function App() {
  const { activePage, setActivePage, theme, setTheme } = useAppStore();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const menuItems = [
    { id: "upload", name: "Ingestion Hub", icon: UploadCloud },
    { id: "validation-center", name: "Validation Core", icon: ShieldCheck },
    { id: "profiles", name: "Profiles", icon: Layers },
    { id: "logs", name: "Audit Trail", icon: History },
    { id: "dashboard", name: "Dashboard", icon: LayoutDashboard },
    { id: "settings", name: "Settings", icon: SettingsIcon }
  ];

  // Sync theme to HTML class list on mount and change
  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  return (
    <div className="flex h-screen bg-black text-neutral-100 overflow-hidden select-none">
      
      {/* Sidebar */}
      <aside className={`${sidebarCollapsed ? "w-[60px]" : "w-64"} relative bg-neutral-950 border-r border-neutral-900 flex flex-col shrink-0 transition-[width] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]`}>

        {/* Floating Sidebar Toggle Button placed on the border (Pro UI/UX, e.g. 21st.dev style) */}
        <button
          onClick={() => setSidebarCollapsed(c => !c)}
          className="absolute -right-3 top-[16px] z-50 flex h-6 w-6 items-center justify-center rounded-full border border-neutral-800 bg-neutral-950 text-neutral-400 shadow-md transition-all duration-200 hover:bg-neutral-900 hover:text-neutral-100 hover:scale-110 active:scale-95 cursor-pointer"
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? (
            <ChevronsRight className="h-3 w-3" />
          ) : (
            <ChevronsLeft className="h-3 w-3" />
          )}
        </button>

        {/* Brand header */}
        <div className={`h-14 border-b border-neutral-900 flex items-center overflow-hidden relative ${
          sidebarCollapsed ? "justify-center px-0" : "px-4"
        }`}>
          <div className={`flex items-center min-w-0 ${
            sidebarCollapsed ? "justify-center" : "gap-3 w-full"
          }`}>
            {/* Database logo: centered when collapsed, left-aligned when expanded */}
            <div className={`h-7 w-7 rounded-md bg-white flex items-center justify-center shrink-0 transition-all duration-250`}>
              <Database className="h-4 w-4 text-black stroke-[2.5]" />
            </div>
            
            {/* Title & subtitle: fades and contracts smoothly */}
            <div className={`overflow-hidden flex flex-col transition-all duration-250 ease-[cubic-bezier(0.4,0,0.2,1)] ${
              sidebarCollapsed ? "w-0 opacity-0 pointer-events-none" : "w-36 opacity-100"
            }`}>
              <h2 className="font-semibold text-sm tracking-tight text-white leading-tight whitespace-nowrap">StackCheck</h2>
            </div>
          </div>
        </div>

        {/* Navigation list */}
        <nav className={`flex-1 py-4 space-y-1 ${sidebarCollapsed ? "px-0" : "px-2.5"}`}>
          {menuItems.map(item => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                title={sidebarCollapsed ? item.name : undefined}
                className={`flex items-center transition-all duration-150 cursor-pointer ${
                  sidebarCollapsed 
                    ? "justify-center h-9 w-9 mx-auto rounded-lg px-0"
                    : "w-full gap-3 px-2.5 py-2.5 rounded-lg text-xs font-medium"
                } ${
                  isActive
                    ? "bg-neutral-900 text-white font-semibold apple-menu-active"
                    : "text-neutral-500 hover:text-neutral-200 hover:bg-neutral-900/45"
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 transition-colors ${isActive ? "text-white" : "text-neutral-500"} ${sidebarCollapsed ? "" : ""}`} />
                <span className={`overflow-hidden whitespace-nowrap text-xs font-medium transition-all duration-250 ease-[cubic-bezier(0.4,0,0.2,1)] ${
                  sidebarCollapsed ? "w-0 opacity-0 pointer-events-none" : "w-auto opacity-100"
                }`}>
                  {item.name}
                </span>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden bg-black">
        
        {/* Top Header Navigation bar */}
        <header className="h-14 border-b border-neutral-900 flex items-center justify-end px-8 bg-neutral-950/20 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-4 text-xs">
            {/* macOS styled Theme Toggle Button */}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="p-1.5 rounded-lg bg-neutral-905 hover:bg-neutral-900 border border-neutral-800 transition-colors text-neutral-500 hover:text-white"
              title={theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme"}
            >
              {theme === "dark" ? <Sun className="h-3.5 w-3.5 text-neutral-400" /> : <Moon className="h-3.5 w-3.5 text-neutral-500" />}
            </button>
          </div>
        </header>

        {/* View Frame */}
        <div className="flex-1 overflow-y-auto p-8 bg-black">
          <div className="max-w-6xl mx-auto">
            {activePage === "dashboard" && <Dashboard />}
            {activePage === "upload" && <Upload />}
            {activePage === "validation-center" && <ValidationCenter />}
            {activePage === "profiles" && <Profiles />}
            {activePage === "logs" && <Logs />}
            {activePage === "settings" && <Settings />}
          </div>
        </div>
      </main>

    </div>
  );
}
