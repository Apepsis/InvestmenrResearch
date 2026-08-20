import React from "react";
import { createRoot } from "react-dom/client";
import InvestmentApp from "@/app/components/InvestmentApp";
import "@/app/globals.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <InvestmentApp />
  </React.StrictMode>,
);
