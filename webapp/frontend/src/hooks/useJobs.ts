import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { QueueItem, SSEDoneEvent, SSEEvent } from "../types";

export interface LogLine {
  level: string;
  message: string;
  ts: number;
}

export interface Job {
  id: string;
  kind: "build" | "enrich" | "batch" | "apply";
  label: string;
  path?: string; // queue-item path (single jobs); undefined for batch
  count?: number; // batch item count
  status: "running" | "completed" | "failed";
  lines: LogLine[];
  result?: Record<string, unknown>;
  finalMessage?: string;
  overwriteConflict?: boolean; // failed because the target folder already exists
  folderName?: string;
}

/**
 * Page-level job runner. Owns the EventSource for every launched job so a job
 * keeps streaming (and stays viewable) after its modal is closed. `onSettled`
 * fires when any job finishes — used to refresh the queue/completed lists.
 */
export function useJobs(onSettled?: () => void) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const sources = useRef<Record<string, EventSource>>({});
  const onSettledRef = useRef(onSettled);
  onSettledRef.current = onSettled;

  const track = useCallback((job: Job) => {
    setJobs((prev) => [job, ...prev.filter((j) => j.id !== job.id)]);

    const es = new EventSource(`/api/jobs/${job.id}/progress`);
    sources.current[job.id] = es;

    es.onmessage = (e) => {
      const event = JSON.parse(e.data) as SSEEvent;
      if (event.type === "log") {
        setJobs((prev) =>
          prev.map((j) => (j.id === job.id ? { ...j, lines: [...j.lines, event] } : j))
        );
        return;
      }
      const done = event as SSEDoneEvent;
      setJobs((prev) =>
        prev.map((j) =>
          j.id === job.id
            ? {
                ...j,
                status: done.type,
                result: done.result,
                finalMessage: done.message,
                overwriteConflict: done.overwrite_conflict ?? false,
                folderName: done.folder_name,
              }
            : j
        )
      );
      es.close();
      delete sources.current[job.id];
      onSettledRef.current?.();
    };

    es.onerror = () => {
      setJobs((prev) =>
        prev.map((j) =>
          j.id === job.id && j.status === "running"
            ? { ...j, status: "failed", finalMessage: "Connection to job stream lost." }
            : j
        )
      );
      es.close();
      delete sources.current[job.id];
    };
  }, []);

  // Close all streams on unmount.
  useEffect(() => {
    const open = sources.current;
    return () => {
      Object.values(open).forEach((es) => es.close());
    };
  }, []);

  const launchApply = useCallback(
    async (
      item: QueueItem,
      opts: { skipDrive: boolean; allowOverwrite?: boolean }
    ): Promise<string> => {
      const res = await api.post<{ job_id: string }>("/jobs/build", {
        jd_path: item.path,
        skip_drive: opts.skipDrive,
        allow_overwrite: opts.allowOverwrite ?? false,
      });
      track({
        id: res.job_id,
        kind: "build",
        label: item.name,
        path: item.path,
        status: "running",
        lines: [],
      });
      return res.job_id;
    },
    [track]
  );

  // Re-launch a failed apply for its source JD (e.g. with override after an
  // overwrite conflict). Reconstructs the queue item from the job.
  const relaunchApply = useCallback(
    (job: Job, opts: { skipDrive: boolean; allowOverwrite?: boolean }) => {
      if (!job.path) return Promise.reject(new Error("Job has no source JD path"));
      const item: QueueItem = {
        name: job.label,
        path: job.path,
        subfolder: "jobs",
        extension: job.path.split(".").pop() ?? "pdf",
      };
      return launchApply(item, opts);
    },
    [launchApply]
  );

  // Clear a failed job's queued JD (delete the input file).
  const deleteQueued = useCallback((path: string): Promise<unknown> => {
    return api.del("/tracking/queue", { path });
  }, []);

  // Capture a JD from a URL or pasted text (server writes a snapshot), then apply.
  const launchApplyFromSource = useCallback(
    async (
      source: { url: string } | { text: string },
      opts: { skipDrive: boolean }
    ): Promise<string> => {
      const endpoint =
        "url" in source ? "/jobs/build/from-url" : "/jobs/build/from-text";
      const res = await api.post<{ job_id: string; snapshot: string }>(endpoint, {
        ...source,
        skip_drive: opts.skipDrive,
      });
      const label =
        "url" in source ? source.url : (res.snapshot.split("/").pop() ?? "Pasted JD");
      track({
        id: res.job_id,
        kind: "build",
        label,
        path: res.snapshot,
        status: "running",
        lines: [],
      });
      return res.job_id;
    },
    [track]
  );

  const launchApplyRerun = useCallback(
    async (
      folderName: string,
      label: string,
      opts: { skipDrive: boolean; model?: string }
    ): Promise<string> => {
      const res = await api.post<{ job_id: string }>("/jobs/build/rerun", {
        folder_name: folderName,
        skip_drive: opts.skipDrive,
        model: opts.model,
      });
      track({
        id: res.job_id,
        kind: "build",
        label,
        status: "running",
        lines: [],
      });
      return res.job_id;
    },
    [track]
  );

  // Launch the assisted autofill (Playwright) step for a built application —
  // gated by the caller on posting_url being set. Runs as a detached backend
  // subprocess; this job only tracks the (early) fill-report step, not the
  // human finishing in the browser (see design.md).
  const launchAutofill = useCallback(
    async (item: {
      folder_name: string;
      entity_id?: string | null;
    }): Promise<string> => {
      const res = await api.post<{ job_id: string }>("/jobs/apply", {
        folder_name: item.folder_name,
        entity_id: item.entity_id ?? undefined,
      });
      track({
        id: res.job_id,
        kind: "apply",
        label: item.folder_name,
        folderName: item.folder_name,
        status: "running",
        lines: [],
      });
      return res.job_id;
    },
    [track]
  );

  const launchEnrich = useCallback(
    async (item: QueueItem): Promise<string> => {
      const res = await api.post<{ job_id: string }>("/jobs/enrich", {
        profile_path: item.path,
      });
      track({
        id: res.job_id,
        kind: "enrich",
        label: item.name,
        path: item.path,
        status: "running",
        lines: [],
      });
      return res.job_id;
    },
    [track]
  );

  const launchBatch = useCallback(
    async (endpoint: string, label: string): Promise<string> => {
      const res = await api.post<{ job_id: string; count: number }>(endpoint, {});
      track({
        id: res.job_id,
        kind: "batch",
        label,
        count: res.count,
        status: "running",
        lines: [],
      });
      return res.job_id;
    },
    [track]
  );

  const launchSchedule = useCallback(
    async (params: {
      mode: "sync" | "async";
      concurrency: number;
      interval_minutes: number;
      start_at: string;
      paths: string[];
    }): Promise<string> => {
      const res = await api.post<{ job_id: string; count: number }>(
        "/jobs/schedule",
        params
      );
      track({
        id: res.job_id,
        kind: "batch",
        label: `Schedule (${res.count} item${res.count !== 1 ? "s" : ""})`,
        count: res.count,
        status: "running",
        lines: [],
      });
      return res.job_id;
    },
    [track]
  );

  const runningJobForPath = useCallback(
    (path: string): Job | undefined =>
      jobs.find((j) => j.path === path && j.status === "running"),
    [jobs]
  );

  const getJob = useCallback(
    (id: string | null): Job | undefined =>
      id ? jobs.find((j) => j.id === id) : undefined,
    [jobs]
  );

  return {
    jobs,
    launchApply,
    launchApplyFromSource,
    relaunchApply,
    deleteQueued,
    launchApplyRerun,
    launchAutofill,
    launchEnrich,
    launchBatch,
    launchSchedule,
    runningJobForPath,
    getJob,
  };
}
