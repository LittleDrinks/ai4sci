import { Activity, GitFork, LogOut, Menu, MessagesSquare, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useWorld } from "../context/WorldContext";
import { ThemeButton } from "./ThemeButton";


const LINKS = [["/map", "地图", GitFork], ["/chat", "对话", MessagesSquare], ["/activity", "活动", Activity]];


function Sidebar({ open, close }) {
  const navigate = useNavigate();
  const exit = () => { close(); navigate("/projects"); };
  return <aside className={`sidebar ${open ? "sidebar-open" : ""}`}><div className="brand"><div className="brand-mark">研</div><div><b>研究世界</b><span>Research World</span></div>
    <button className="icon-button sidebar-close" onClick={close} title="关闭导航"><X size={19} /></button></div>
    <nav>{LINKS.map(([to, label, Icon]) => <NavLink key={to} to={to} onClick={close}><Icon size={18} /><span>{label}</span></NavLink>)}</nav>
    <button className="sidebar-exit" onClick={exit}><LogOut size={18} /><span>退出项目</span></button></aside>;
}


function Topbar({ openNav }) {
  const { data, projectId, streamState } = useWorld();
  const project = data.projects.find((item) => item.id === projectId);
  return <header className="topbar"><button className="icon-button menu-button" onClick={openNav} title="打开导航"><Menu size={20} /></button>
    <div className="project-context"><b>{project?.title}</b><span>{project?.question}</span></div>
    <div className={`connection ${streamState}`}><i />{streamState === "live" ? "实时" : "同步中"}</div><ThemeButton /></header>;
}


function ErrorToast() {
  const { error, setError } = useWorld();
  if (!error) return null;
  return <div className="error-toast" role="alert"><span>{error}</span><button className="icon-button" onClick={() => setError("")} title="关闭提示"><X size={18} /></button></div>;
}


export function AppShell() {
  const [navOpen, setNavOpen] = useState(false);
  return <div className="app-shell"><Sidebar open={navOpen} close={() => setNavOpen(false)} /><div className="app-main">
    <Topbar openNav={() => setNavOpen(true)} /><main className="page-host"><Outlet /></main></div><ErrorToast /></div>;
}
