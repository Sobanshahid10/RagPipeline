"use client";
import React from "react";
import { QueryMetadata } from "@/lib/api";
export const RAGPipelineInspector: React.FC<{metadata?:QueryMetadata}> = ({metadata}) => {
  if (!metadata) return null;
  return <details style={{marginTop:12,fontSize:12}}><summary>Answer details</summary>
    <p>Model: {metadata.actual_model || "Unavailable"}</p>
    <p>Provider: {metadata.actual_provider || "Unavailable"}</p>
    <p>Total response time: {metadata.total_latency_ms === undefined ? "Unavailable" : `${metadata.total_latency_ms} ms`}</p>
    <p>Retrieved passages: {metadata.chunks_retrieved ?? "Unavailable"}</p>
    <p>Validation: {metadata.validation || "Unavailable"}</p>
  </details>;
};
