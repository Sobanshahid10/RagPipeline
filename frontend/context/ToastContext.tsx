"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export type ToastType = "success" | "error" | "info";

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastContextType {
  showToast: (type: ToastType, title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType>({
  showToast: () => {},
});

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((type: ToastType, title: string, message?: string) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const getIcon = (type: ToastType) => {
    switch (type) {
      case "success":
        return <CheckCircle2 size={18} color="#10B981" />;
      case "error":
        return <AlertCircle size={18} color="#F43F5E" />;
      case "info":
        return <Info size={18} color="#6366F1" />;
    }
  };

  const getBorderColor = (type: ToastType) => {
    switch (type) {
      case "success":
        return "rgba(16, 185, 129, 0.4)";
      case "error":
        return "rgba(244, 63, 94, 0.4)";
      case "info":
        return "rgba(99, 102, 241, 0.4)";
    }
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast Container */}
      <div
        style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          pointerEvents: "none",
          maxWidth: "380px",
          width: "100%",
        }}
      >
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              style={{
                pointerEvents: "auto",
                background: "rgba(18, 20, 31, 0.92)",
                backdropFilter: "blur(16px)",
                border: `1px solid ${getBorderColor(toast.type)}`,
                borderRadius: "12px",
                padding: "14px 16px",
                display: "flex",
                alignItems: "flex-start",
                gap: "12px",
                boxShadow: "0 10px 30px rgba(0, 0, 0, 0.5)",
              }}
            >
              <div style={{ marginTop: "2px", flexShrink: 0 }}>{getIcon(toast.type)}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: "13.5px",
                    fontWeight: 600,
                    color: "#FFFFFF",
                    lineHeight: 1.3,
                  }}
                >
                  {toast.title}
                </div>
                {toast.message && (
                  <div
                    style={{
                      fontSize: "12.5px",
                      color: "var(--text-secondary)",
                      marginTop: "3px",
                      lineHeight: 1.4,
                    }}
                  >
                    {toast.message}
                  </div>
                )}
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "2px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <X size={15} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => useContext(ToastContext);
