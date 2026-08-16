import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";


function initialTheme() {
  return localStorage.getItem("rw-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}


export function ThemeButton() {
  const [theme, setTheme] = useState(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("rw-theme", theme);
  }, [theme]);
  const dark = theme === "dark";
  const label = dark ? "切换浅色模式" : "切换深色模式";
  return <button className="icon-button theme-button" aria-label={label} title={label} onClick={() => setTheme(dark ? "light" : "dark")}>
    {dark ? <Sun size={18} /> : <Moon size={18} />}</button>;
}
