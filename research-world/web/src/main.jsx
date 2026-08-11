import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { WorldProvider } from "./context/WorldContext";
import "@xyflow/react/dist/style.css";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <WorldProvider><App /></WorldProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
