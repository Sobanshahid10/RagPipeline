"use client";
import * as Dialog from "@radix-ui/react-dialog";
import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { configuredModels, chatHistoryKey, deleteServerHistory } from "@/lib/api";
import { DEFAULT_MODEL, MODEL_OPTIONS } from "@/lib/models";

export const SettingsModal: React.FC<{isOpen:boolean;onClose:()=>void}> = ({isOpen,onClose}) => {
  const {user,token}=useAuth();
  const {showToast}=useToast();
  const [model,setModel]=useState<string>(DEFAULT_MODEL);
  const [available,setAvailable]=useState<string[]>([]);
  const [error,setError]=useState("");
  const [deleting,setDeleting]=useState(false);
  useEffect(() => {
    if (!isOpen || !token) return;
    setError("");
    configuredModels(token).then(ids => {
      setAvailable(ids);
      let saved="";
      try {saved=JSON.parse(localStorage.getItem("rag_settings") || "{}").llmModel || "";} catch {}
      setModel(ids.includes(saved) ? saved : ids[0] || "");
    }).catch(err => setError(err.message));
  },[isOpen,token]);
  if (!isOpen) return null;
  return <Dialog.Root open={isOpen} onOpenChange={open => {if(!open)onClose();}}><Dialog.Portal>
    <Dialog.Overlay style={{position:"fixed",inset:0,background:"rgba(0,0,0,.75)",zIndex:9999}} />
    <Dialog.Content style={{position:"fixed",left:"50%",top:"50%",transform:"translate(-50%,-50%)",zIndex:10000,background:"var(--surface)",padding:24,borderRadius:12,maxWidth:520,width:"calc(100% - 40px)",maxHeight:"90vh",overflowY:"auto",display:"flex",flexDirection:"column",gap:14}}>
      <Dialog.Title style={{fontSize:22,fontWeight:700}}>Settings</Dialog.Title>
      <Dialog.Description style={{color:"var(--text-secondary)",fontSize:14}}>Choose the default answer model. Requests use exactly this model and provider.</Dialog.Description>
      {error && <p role="alert">{error}</p>}
      <label>Answer model<select className="input-field" value={model} onChange={e=>setModel(e.target.value)}>
        {!available.length && <option value="">No configured providers</option>}
        {MODEL_OPTIONS.filter(m=>available.includes(m.id)).map(m=><option key={m.id} value={m.id}>{m.label}</option>)}
      </select></label>
      <p>Workspace: {user?.tenant?.name || "Unavailable"}</p>
      <p>Account: {user?.email || "Unavailable"}</p>
      <p>Roles: {user?.roles?.join(", ") || "Unavailable"}</p>
      <button className="btn btn-secondary" onClick={()=>{const key=chatHistoryKey(user);if(key)localStorage.removeItem(key);window.dispatchEvent(new Event("rag-history-cleared"));window.dispatchEvent(new Event("rag-sessions-updated"));showToast("success","Local chat history cleared");}}>Clear this account’s local history</button>
      <button className="btn btn-secondary" disabled={deleting} onClick={async()=>{if(!token || !window.confirm("Delete all of your saved server interactions? This cannot be undone."))return;setDeleting(true);try{await deleteServerHistory(token);showToast("success","Saved server interactions deleted");}catch(err){setError(err instanceof Error?err.message:"Deletion failed");}finally{setDeleting(false);}}}>Delete my saved server interactions</button>
      <p style={{fontSize:13,color:"var(--text-secondary)"}}>History is stored separately for each account in this browser. Original documents remain stored until deleted from Documents.</p>
      <div style={{display:"flex",gap:12,marginTop:20}}>
        <button className="btn btn-secondary" onClick={onClose}>Close</button>
        <button className="btn btn-primary" disabled={!available.includes(model)} onClick={()=>{localStorage.setItem("rag_settings",JSON.stringify({llmModel:model}));window.dispatchEvent(new Event("rag-model-change"));showToast("success","Answer model saved");onClose();}}>Save model</button>
      </div>
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>;
};
