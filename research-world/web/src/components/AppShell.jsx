import { useState } from "react";
import { Activity, Bot, CheckCheck, ChevronDown, FileText, GitFork, ListTodo, Menu, Plus, X } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useWorld } from "../context/WorldContext";
import { displayError } from "../utils";
import { NewProjectDialog } from "./NewProjectDialog";

const LINKS = [["/map", "地图", GitFork], ["/review", "审核", CheckCheck], ["/activity", "活动", Activity], ["/queue", "队列", ListTodo], ["/agents", "智能体", Bot], ["/reports", "报告", FileText]];

function Sidebar({ open, close }) {
  return <aside className={`sidebar ${open ? "sidebar-open" : ""}`}><div className="brand"><div className="brand-mark">研</div><div><b>研究世界</b><span>本地控制平面</span></div><button className="icon-button sidebar-close" onClick={close} title="关闭导航"><X size={20} /></button></div>
    <nav>{LINKS.map(([to, label, Icon]) => <NavLink key={to} to={to} onClick={close}><Icon size={19} /><span>{label}</span></NavLink>)}</nav>
    <div className="sidebar-foot"><span className="local-dot" />本地工作区</div>
  </aside>;
}

function ProjectSelect() {
  const { projects, projectId, selectProject } = useProjectData();
  if (!projects.length) return <span className="project-empty">未选择项目</span>;
  return <label className="project-select"><span className="sr-only">项目</span><select value={projectId} onChange={(event) => selectProject(event.target.value)}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select><ChevronDown size={16} /></label>;
}

function useProjectData() {
  const { data, projectId, selectProject } = useWorld();
  return { projects: data.projects || [], projectId, selectProject };
}

function Topbar({ openNav, openProject }) {
  const { data, projectId, streamState } = useWorld();
  const project = data.projects.find((item) => item.id === projectId);
  return <header className="topbar"><button className="icon-button menu-button" onClick={openNav} title="打开导航"><Menu size={20} /></button><div className="topbar-context"><ProjectSelect /><span>{project?.question || "请选择一个命题开始"}</span></div><div className={`connection ${streamState}`}><i />{streamState === "live" ? "实时" : "同步中"}</div><button className="button primary" onClick={openProject}><Plus size={17} />新建项目</button></header>;
}

function ErrorToast() {
  const { error, setError } = useWorld();
  if (!error) return null;
  return <div className="error-toast" role="alert"><span>{displayError(error)}</span><button className="icon-button" onClick={() => setError("")} title="关闭提示"><X size={18} /></button></div>;
}

export function AppShell() {
  const [navOpen, setNavOpen] = useState(false);
  const [projectOpen, setProjectOpen] = useState(false);
  return <div className="app-shell"><Sidebar open={navOpen} close={() => setNavOpen(false)} /><div className="app-main"><Topbar openNav={() => setNavOpen(true)} openProject={() => setProjectOpen(true)} /><main className="page-host"><Outlet /></main></div><ErrorToast /><NewProjectDialog open={projectOpen} onClose={() => setProjectOpen(false)} /></div>;
}
