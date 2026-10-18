import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

const measurePageLoad = () => {
  requestAnimationFrame(() => {
    const navigation = performance.getEntriesByType("navigation")[0];
    if (navigation) {
      const endTime = navigation.loadEventEnd || performance.now();
      performance.measure("page-load", {
        start: navigation.startTime,
        end: endTime,
      });
    }
  });
};

if (document.readyState === "complete") {
  measurePageLoad();
} else {
  window.addEventListener("load", measurePageLoad, { once: true });
}
