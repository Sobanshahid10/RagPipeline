"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { ArrowUpRight, X } from "lucide-react";
import styles from "./ProjectOwnerCard.module.css";

export function ProjectOwnerCard() {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button type="button" className={styles.trigger} aria-label="About Muhammad Soban, repository owner" title="About the project owner">
          MS
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content className={styles.card} aria-describedby={undefined}>
          <Dialog.Close asChild>
            <button type="button" className={styles.close} aria-label="Close project owner card"><X size={20} /></button>
          </Dialog.Close>
          <div className={styles.profile}>
            <p className={styles.eyebrow}>THE PERSON BEHIND THE PROJECT</p>
            <div className={styles.avatar} aria-hidden="true">MS</div>
            <Dialog.Title className={styles.name}>Muhammad Soban</Dialog.Title>
            <p className={styles.role}>AI &amp; Frontend Engineer</p>
          </div>
          <div className={styles.education}>
            <p className={styles.degree}>BS Artificial Intelligence</p>
            <p>University of Management and Technology</p>
            <p className={styles.location}>Lahore, Pakistan</p>
          </div>
          <div className={styles.actions}>
            <a className={styles.repository} href="https://github.com/Sobanshahid10/RagPipeline" target="_blank" rel="noopener noreferrer">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 .75a11.25 11.25 0 0 0-3.558 21.923c.563.104.769-.244.769-.542 0-.267-.01-.975-.015-1.913-3.13.68-3.79-1.508-3.79-1.508-.512-1.3-1.25-1.646-1.25-1.646-1.022-.699.078-.685.078-.685 1.13.08 1.725 1.16 1.725 1.16 1.005 1.721 2.637 1.224 3.28.936.102-.728.393-1.224.715-1.506-2.499-.284-5.126-1.25-5.126-5.563 0-1.229.44-2.234 1.16-3.021-.116-.285-.503-1.43.11-2.98 0 0 .945-.303 3.094 1.154A10.79 10.79 0 0 1 12 6.19c.956.005 1.918.129 2.817.379 2.148-1.457 3.091-1.154 3.091-1.154.615 1.55.228 2.695.112 2.98.722.787 1.158 1.792 1.158 3.021 0 4.324-2.631 5.276-5.138 5.554.404.349.765 1.034.765 2.084 0 1.505-.014 2.719-.014 3.088 0 .301.203.652.774.541A11.252 11.252 0 0 0 12 .75Z" />
              </svg>
              <span><strong>GitHub repository</strong><small>Explore Soban’s RAG Pipeline</small></span>
              <ArrowUpRight size={20} aria-hidden="true" />
            </a>
            <a className={styles.portfolio} href="https://omerfarooq223.github.io" target="_blank" rel="noopener noreferrer">
              <span><strong>Visit portfolio</strong><small>Muhammad Umar Farooq · Collaborator</small></span>
              <ArrowUpRight size={20} aria-hidden="true" />
            </a>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
