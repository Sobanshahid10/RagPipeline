"use client";
import React, {useState} from "react";
import {useRouter} from "next/navigation";
import {DocumentItem,retryDocument} from "@/lib/api";
import {useAuth} from "@/context/AuthContext";
import {useToast} from "@/context/ToastContext";
export const DocumentDrawer: React.FC<{document:DocumentItem|null;onClose:()=>void}> = ({document:doc,onClose}) => {
  const {token,user}=useAuth(); const router=useRouter(); const {showToast}=useToast(); const [busy,setBusy]=useState(false);
  if (!doc) return null;
  return <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,.7)",zIndex:9999,display:"flex",justifyContent:"flex-end"}} onClick={onClose}>
    <section role="dialog" aria-modal="true" aria-label="Document details" style={{width:480,maxWidth:"100%",background:"var(--surface)",padding:24,overflowY:"auto",display:"flex",flexDirection:"column",gap:14}} onClick={e=>e.stopPropagation()}>
      <button className="btn btn-ghost" onClick={onClose}>Close</button><h2>{doc.filename}</h2>
      <p>Status: {doc.stalled ? "Stalled — retry available" : doc.status}</p><p>Stage: {doc.stage || "Unavailable"}</p>
      <p>Pages: {doc.total_pages} · Chunks: {doc.chunk_count}</p>
      {doc.graph_status && <p>Graph extraction: {doc.graph_status}</p>}
      {doc.error && <p role="alert">{doc.error}</p>}
      <p>Original files are retained until deleted. Only indexed documents are used for answers.</p>
      <button className="btn btn-secondary" onClick={()=>router.push(`/documents/${doc.document_id}`)}>Open document</button>
      {doc.status==="indexed" && <button className="btn btn-secondary" onClick={()=>router.push(`/chat?document=${doc.document_id}`)}>Ask about this document</button>}
      {(doc.status==="failed" || doc.status==="indexed" || doc.stalled) && user?.roles?.some(r=>["admin","editor"].includes(r)) && <button className="btn btn-primary" disabled={busy} onClick={async()=>{if(!token)return;setBusy(true);try{await retryDocument(doc.document_id,token);showToast("success","Document queued for retry");onClose();}catch(err){showToast("error","Retry failed",err instanceof Error?err.message:"Retry failed");}finally{setBusy(false);}}}>{doc.status === "indexed" ? "Reindex document" : "Retry processing"}</button>}
    </section>
  </div>;
};
