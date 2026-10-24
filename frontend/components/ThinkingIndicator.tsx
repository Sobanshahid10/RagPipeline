"use client";

import { MessageSquare } from "lucide-react";
import styles from "./ThinkingIndicator.module.css";

export function ThinkingIndicator({ phase }: { phase: string }) {
  return (
    <div className={styles.indicator} role="status" aria-live="polite">
      <div className={styles.icon} aria-hidden="true"><MessageSquare size={16} /></div>
      <div>
        <div className={styles.heading}>
          <span className={styles.label}>Thinking</span>
          <span className={styles.dots} aria-hidden="true"><i /><i /><i /></span>
        </div>
        <p className={styles.phase}>{phase}</p>
      </div>
    </div>
  );
}
