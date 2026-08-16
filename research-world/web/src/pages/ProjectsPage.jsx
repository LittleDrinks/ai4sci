import { ArrowRight, FolderOpen, Plus } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { NewProjectDialog } from "../components/NewProjectDialog";
import { ThemeButton } from "../components/ThemeButton";
import { useWorld } from "../context/WorldContext";
import "../projects.css";


export function ProjectsPage() {
  const { data, loading, projectId, selectProject } = useWorld();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const enter = async (id) => { await selectProject(id); navigate("/map"); };
  return <section className="projects-page"><ProjectBar onNew={() => setOpen(true)} /><main><header><span>工作区</span><h1>选择研究项目</h1></header>
    {loading ? <div className="projects-loading">正在载入项目...</div> : <ProjectList projects={data.projects} activeId={projectId} onOpen={enter} onNew={() => setOpen(true)} />}</main>
    <NewProjectDialog open={open} onClose={() => setOpen(false)} /></section>;
}


function ProjectBar({ onNew }) {
  return <header className="projects-bar"><div className="projects-brand"><span>研</span><div><b>研究世界</b><small>Research World</small></div></div>
    <div><ThemeButton /><button className="button primary" onClick={onNew}><Plus size={16} />新建项目</button></div></header>;
}


function ProjectList({ projects, activeId, onOpen, onNew }) {
  if (!projects.length) return <section className="projects-empty"><FolderOpen size={28} /><h2>暂无研究项目</h2><button className="button primary" onClick={onNew}><Plus size={16} />新建项目</button></section>;
  return <div className="project-list">{projects.map((project) => <button className={project.id === activeId ? "active" : ""} onClick={() => onOpen(project.id)} key={project.id}>
    <span className="project-name"><b>{project.title}</b><small>{project.question}</small></span><span className="project-counts"><b>{project.node_count}</b> 节点 · <b>{project.workflow_count}</b> 工作流</span>
    <time>{formatDate(project.created_at)}</time><ArrowRight size={18} /></button>)}</div>;
}


function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(value));
}
