import { FormEvent, PointerEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AuthSession,
  clearStoredSession,
  getValidSession,
  signInWithPassword,
  signOut,
  signUpWithPassword,
} from "./auth_client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type Role = "user" | "assistant";

type Message = {
  id: string;
  role: Role;
  content: string;
};

type Job = {
  id?: string;
  source?: string;
  title?: string;
  description?: string;
  org_name?: string;
  cities?: string[];
  remote?: boolean;
  work_mode?: string;
  country?: string;
  stipend_display?: string;
  salary_display?: string;
  duration_display?: string;
  skills?: string[];
  categories?: string[];
  eligibility?: string[];
  benefits?: string[];
  work_functions?: string[];
  source_url?: string;
  application_url?: string;
  rerank_score?: number;
};

type ResumeData = {
  summary?: string;
  skills?: string[];
  technologies?: string[];
  domains?: string[];
};

type ResumeUploadResponse = {
  parsed_data: ResumeData;
  preview_url?: string;
  thumbnail_url?: string;
  original_filename?: string;
};

type CurrentResumeResponse = {
  has_resume: boolean;
  resume?: {
    file_name?: string;
    parsed_data?: ResumeData;
    preview_url?: string;
    thumbnail_url?: string;
  } | null;
};

type JobsResponse = {
  jobs: Job[];
  count: number;
};

type JobDetailsResponse = {
  job: Job;
};

type VoiceState = "idle" | "listening" | "transcribing";

const CATEGORY_OPTIONS = [
  "accounts",
  "ai agent development",
  "android app development",
  "backend development",
  "bank",
  "cad design",
  "chartered accountancy",
  "cloud computing",
  "cyber security",
  "electronics",
  "engineering",
  "front end development",
  "full stack development",
  "human resources",
  "product",
  "teaching",
];

function createId() {
  if ("crypto" in window && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getJobLocation(job: Job) {
  if (job.remote) {
    return "Remote";
  }

  if (job.cities?.length) {
    return job.cities.map(formatDisplayLabel).join(", ");
  }

  return "Location not listed";
}

function getJobDetailLocation(job: Job) {
  const location = getJobLocation(job);
  if (location !== "Location not listed") {
    return location;
  }

  return job.country ?? "Not given";
}

function renderDetailList(values?: string[], ordered = false) {
  if (!values?.length) {
    return <p className="muted">Not given</p>;
  }

  if (ordered) {
    return (
      <div className="job-detail-numbered-list">
        {values.map((value, index) => (
          <p key={value}>
            <span>{index + 1}.</span>
            {value}
          </p>
        ))}
      </div>
    );
  }

  return (
    <ul>
      {values.map((value) => (
        <li key={value}>{value}</li>
      ))}
    </ul>
  );
}

function formatDisplayLabel(value: string) {
  return value
    .split(/(\s+|-|\/)/)
    .map((part) => {
      if (!part.trim() || part === "-" || part === "/") {
        return part;
      }

      const lower = part.toLowerCase();
      return `${lower.charAt(0).toUpperCase()}${lower.slice(1)}`;
    })
    .join("");
}

function formatSkillLabel(skill: string) {
  const uppercaseTerms = new Set([
    "api",
    "aws",
    "css",
    "gcp",
    "html",
    "llm",
    "nlp",
    "rag",
    "seo",
    "sql",
    "ui",
    "ux",
  ]);

  return skill
    .split(/(\s+|-|\/)/)
    .map((part) => {
      const clean = part.toLowerCase();

      if (!clean.trim() || part === "-" || part === "/") {
        return part;
      }

      if (uppercaseTerms.has(clean) || clean.includes("+") || clean.includes("#")) {
        return clean.toUpperCase();
      }

      if (clean === "node.js") {
        return "Node.js";
      }

      if (clean === "next.js") {
        return "Next.js";
      }

      return `${clean.charAt(0).toUpperCase()}${clean.slice(1)}`;
    })
    .join("");
}

function authHeaders(session: AuthSession) {
  return {
    Authorization: `Bearer ${session.access_token}`,
  };
}

function getChatStorageKey(session: AuthSession) {
  return `joblens_chat_id:${session.user.id}`;
}

async function createChatSession(session: AuthSession) {
  const response = await fetch(`${API_BASE_URL}/chat/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(session),
    },
    body: JSON.stringify({
      title: "Job search",
    }),
  });

  if (!response.ok) {
    throw new Error("Could not create chat session");
  }

  return response.json() as Promise<{ chat_id: string }>;
}

function parseSseBlock(block: string) {
  const lines = block.split("\n");
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (!dataLines.length) {
    return null;
  }

  return {
    event,
    data: JSON.parse(dataLines.join("\n")),
  };
}

async function uploadResume(session: AuthSession, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/pdf/upload`, {
    method: "POST",
    headers: authHeaders(session),
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Resume upload failed");
  }

  return response.json() as Promise<ResumeUploadResponse>;
}

async function getCurrentResume(session: AuthSession) {
  const response = await fetch(`${API_BASE_URL}/pdf/current`, {
    headers: authHeaders(session),
  });

  if (!response.ok) {
    throw new Error("Could not load resume");
  }

  return response.json() as Promise<CurrentResumeResponse>;
}

async function fetchJobs(filters: {
  q?: string;
  workMode?: string;
  categories?: string[];
  paid?: string;
}) {
  const params = new URLSearchParams();

  if (filters.q?.trim()) {
    params.set("q", filters.q.trim());
  }

  if (filters.workMode) {
    params.set("work_mode", filters.workMode);
  }

  for (const category of filters.categories ?? []) {
    params.append("category", category);
  }

  if (filters.paid) {
    params.set("paid", filters.paid);
  }

  params.set("limit", "80");

  const response = await fetch(`${API_BASE_URL}/jobs?${params.toString()}`);

  if (!response.ok) {
    throw new Error("Could not load jobs");
  }

  return response.json() as Promise<JobsResponse>;
}

async function fetchJobDetails(jobId: string) {
  const response = await fetch(`${API_BASE_URL}/jobs/${encodeURIComponent(jobId)}`);

  if (!response.ok) {
    throw new Error("Could not load job details");
  }

  return response.json() as Promise<JobDetailsResponse>;
}

async function transcribeVoiceInput(session: AuthSession, audio: Blob) {
  const extension = audio.type.includes("mp4") ? "mp4" : "webm";
  const formData = new FormData();
  formData.append("file", audio, `voice-input.${extension}`);

  const response = await fetch(`${API_BASE_URL}/voice/transcribe`, {
    method: "POST",
    headers: authHeaders(session),
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Voice transcription failed");
  }

  return response.json() as Promise<{ text: string }>;
}

export default function App() {
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const [authName, setAuthName] = useState("Tarandeep");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [showAuthPassword, setShowAuthPassword] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authNotice, setAuthNotice] = useState<string | null>(null);
  const [chatId, setChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobDetailsLoading, setJobDetailsLoading] = useState(false);
  const [jobDetailsError, setJobDetailsError] = useState<string | null>(null);
  const [jobSearch, setJobSearch] = useState("");
  const [workModeFilter, setWorkModeFilter] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [paidFilter, setPaidFilter] = useState("");
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Ready");
  const [chatProgress, setChatProgress] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [resume, setResume] = useState<ResumeData | null>(null);
  const [resumeFileName, setResumeFileName] = useState<string | null>(null);
  const [resumePreviewUrl, setResumePreviewUrl] = useState<string | null>(null);
  const [resumeThumbnailUrl, setResumeThumbnailUrl] = useState<string | null>(null);
  const [isResumePreviewOpen, setIsResumePreviewOpen] = useState(false);
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const [useResumeProfile, setUseResumeProfile] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [jobsWidth, setJobsWidth] = useState(420);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const workspaceRef = useRef<HTMLElement | null>(null);
  const categoryMenuRef = useRef<HTMLDetailsElement | null>(null);
  const accountMenuRef = useRef<HTMLDivElement | null>(null);
  const localResumePreviewUrlRef = useRef<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const voiceStreamRef = useRef<MediaStream | null>(null);
  const accountName =
    authSession?.user.user_metadata?.name ||
    authSession?.user.user_metadata?.full_name ||
    authSession?.user.email?.split("@")[0] ||
    "Account";

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      const session = await getValidSession();
      if (!cancelled) {
        setAuthSession(session);
        setAuthLoading(false);
      }
    }

    loadSession();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!authSession) {
      setChatId(null);
      return;
    }

    setChatId(localStorage.getItem(getChatStorageKey(authSession)));
  }, [authSession]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 170)}px`;
    textarea.style.overflowY = textarea.scrollHeight > 170 ? "auto" : "hidden";
  }, [input]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsResumePreviewOpen(false);
        setSelectedJob(null);
        setIsAccountMenuOpen(false);
        categoryMenuRef.current?.removeAttribute("open");
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    function handlePointerDown(event: globalThis.PointerEvent) {
      const menu = categoryMenuRef.current;

      if (!menu || !menu.open || menu.contains(event.target as Node)) {
        return;
      }

      menu.removeAttribute("open");
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  useEffect(() => {
    function handlePointerDown(event: globalThis.PointerEvent) {
      const menu = accountMenuRef.current;

      if (!menu || menu.contains(event.target as Node)) {
        return;
      }

      setIsAccountMenuOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  useEffect(() => {
    return () => {
      if (localResumePreviewUrlRef.current) {
        URL.revokeObjectURL(localResumePreviewUrlRef.current);
      }

      voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadResume() {
      if (!authSession) {
        return;
      }

      try {
        const result = await getCurrentResume(authSession);
        if (cancelled || !result.has_resume || !result.resume) {
          return;
        }

        setResume(result.resume.parsed_data ?? null);
        setResumeFileName(result.resume.file_name ?? "Uploaded resume");
        setResumePreviewUrl(result.resume.preview_url ?? null);
        setResumeThumbnailUrl(result.resume.thumbnail_url ?? null);
        setUseResumeProfile(Boolean(result.resume.parsed_data));
      } catch {
        setStatus("Ready");
      }
    }

    loadResume();

    return () => {
      cancelled = true;
    };
  }, [authSession]);

  useEffect(() => {
    let cancelled = false;
    const timeout = window.setTimeout(async () => {
      setJobsLoading(true);

      try {
        const result = await fetchJobs({
          q: jobSearch,
          workMode: workModeFilter,
          categories: selectedCategories,
          paid: paidFilter,
        });

        if (!cancelled) {
          setJobs(result.jobs ?? []);
        }
      } catch {
        if (!cancelled) {
          setStatus("Could not load jobs");
        }
      } finally {
        if (!cancelled) {
          setJobsLoading(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [jobSearch, workModeFilter, selectedCategories, paidFilter]);

  function toggleCategory(category: string) {
    setSelectedCategories((current) =>
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category]
    );
  }

  function getCategorySummary() {
    if (!selectedCategories.length) {
      return "Any";
    }

    if (selectedCategories.length === 1) {
      return formatDisplayLabel(selectedCategories[0]);
    }

    return `${selectedCategories.length} selected`;
  }

  async function ensureChatSession() {
    if (!authSession) {
      throw new Error("Please sign in again");
    }

    if (chatId) {
      return chatId;
    }

    const session = await createChatSession(authSession);
    localStorage.setItem(getChatStorageKey(authSession), session.chat_id);
    setChatId(session.chat_id);
    return session.chat_id;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();

    const query = input.trim();
    if (!query || isStreaming || !authSession) {
      return;
    }

    const sessionId = await ensureChatSession();
    const assistantId = createId();

    setInput("");
    setStatus("Ready");
    setChatProgress(null);
    setIsStreaming(true);
    setMessages((current) => [
      ...current,
      { id: createId(), role: "user", content: query },
      { id: assistantId, role: "assistant", content: "" },
    ]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(authSession),
        },
        body: JSON.stringify({
          query,
          chat_id: sessionId,
          use_resume_profile: useResumeProfile && Boolean(resume),
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Chat stream failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";

        for (const block of blocks) {
          const parsed = parseSseBlock(block);
          if (!parsed) {
            continue;
          }

          if (parsed.event === "status") {
            setStatus(parsed.data.text);
            setChatProgress(parsed.data.text);
          }

          if (parsed.event === "jobs") {
            const jobsCount = (parsed.data.jobs ?? []).length;
            setStatus(`${jobsCount} recommendations found`);
            setChatProgress(`${jobsCount} recommendations found`);
          }

          if (parsed.event === "token") {
            setChatProgress(null);
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? { ...message, content: message.content + parsed.data.text }
                  : message
              )
            );
          }

          if (parsed.event === "done") {
            setStatus("Done");
            setChatProgress(null);
          }

          if (parsed.event === "error") {
            throw new Error(parsed.data.message ?? "Stream error");
          }
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong";
      setStatus(message);
      setChatProgress(null);
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId
            ? { ...item, content: `Error: ${message}` }
            : item
        )
      );
    } finally {
      setIsStreaming(false);
    }
  }

  function stopVoiceTracks() {
    voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
    voiceStreamRef.current = null;
  }

  async function handleRecordedAudio(audio: Blob) {
    if (!authSession) {
      return;
    }

    setVoiceState("transcribing");
    setVoiceError(null);
    setStatus("Transcribing...");

    try {
      const result = await transcribeVoiceInput(authSession, audio);
      const transcript = result.text.trim();

      if (!transcript) {
        throw new Error("No speech detected");
      }

      setInput((current) => {
        const trimmed = current.trim();
        return trimmed ? `${trimmed} ${transcript}` : transcript;
      });
      setStatus("Transcript ready");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Voice transcription failed";
      setVoiceError(message);
      setStatus(message);
    } finally {
      stopVoiceTracks();
      setVoiceState("idle");
    }
  }

  async function startVoiceRecording() {
    if (!authSession || isStreaming || voiceState !== "idle") {
      return;
    }

    if (!("mediaDevices" in navigator) || !window.MediaRecorder) {
      setVoiceError("Voice input is not supported in this browser");
      setStatus("Voice input is not supported in this browser");
      return;
    }

    try {
      setVoiceError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "";
      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined
      );

      audioChunksRef.current = [];
      voiceStreamRef.current = stream;
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const audio = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        void handleRecordedAudio(audio);
      };

      recorder.start();
      setVoiceState("listening");
      setStatus("Listening...");
    } catch (error) {
      stopVoiceTracks();
      const message =
        error instanceof Error ? error.message : "Could not access microphone";
      setVoiceError(message);
      setStatus(message);
      setVoiceState("idle");
    }
  }

  function stopVoiceRecording() {
    const recorder = mediaRecorderRef.current;

    if (!recorder || recorder.state === "inactive") {
      return;
    }

    recorder.stop();
    setStatus("Transcribing...");
    setVoiceState("transcribing");
  }

  function handleVoiceButtonClick() {
    if (voiceState === "listening") {
      stopVoiceRecording();
      return;
    }

    void startVoiceRecording();
  }

  async function handleResumeChange(fileList: FileList | null) {
    const file = fileList?.[0];

    if (!file || !authSession) {
      return;
    }

    setUploading(true);
    setStatus("Uploading resume");

    const previewUrl = URL.createObjectURL(file);
    if (localResumePreviewUrlRef.current) {
      URL.revokeObjectURL(localResumePreviewUrlRef.current);
    }
    localResumePreviewUrlRef.current = previewUrl;

    setResumeFileName(file.name);
    setResumePreviewUrl(previewUrl);

    try {
      const result = await uploadResume(authSession, file);
      setResume(result.parsed_data);
      setResumeFileName(result.original_filename ?? file.name);
      if (result.preview_url) {
        if (localResumePreviewUrlRef.current) {
          URL.revokeObjectURL(localResumePreviewUrlRef.current);
          localResumePreviewUrlRef.current = null;
        }
        setResumePreviewUrl(result.preview_url);
      }
      setResumeThumbnailUrl(result.thumbnail_url ?? null);
      setUseResumeProfile(true);
      setStatus("Resume ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Resume upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function openJobDetails(job: Job) {
    if (!job.id) {
      setJobDetailsError("Job details are not available for this listing.");
      return;
    }

    setSelectedJob(job);
    setJobDetailsError(null);
    setJobDetailsLoading(true);

    try {
      const result = await fetchJobDetails(job.id);
      setSelectedJob(result.job);
    } catch (error) {
      setJobDetailsError(
        error instanceof Error ? error.message : "Could not load job details"
      );
    } finally {
      setJobDetailsLoading(false);
    }
  }

  function startNewChat() {
    if (authSession) {
      localStorage.removeItem(getChatStorageKey(authSession));
    }
    setChatId(null);
    setMessages([]);
    setChatProgress(null);
    setStatus("Ready");
  }

  async function handleAuthSubmit(event: FormEvent) {
    event.preventDefault();
    setAuthError(null);
    setAuthNotice(null);
    setAuthLoading(true);

    try {
      const session =
        authMode === "signin"
          ? await signInWithPassword(authEmail.trim(), authPassword)
          : await signUpWithPassword(
              authEmail.trim(),
              authPassword,
              authName.trim() || "JobLens User"
            );

      if (!session) {
        setAuthMode("signin");
        setAuthPassword("");
        setAuthNotice(
          "Account created. Check your email to confirm it, then sign in."
        );
        return;
      }

      setAuthSession(session);
      setStatus("Ready");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleSignOut() {
    await signOut(authSession);
    if (authSession) {
      localStorage.removeItem(getChatStorageKey(authSession));
    }
    localStorage.removeItem("joblens_chat_id");
    clearStoredSession();
    setAuthSession(null);
    setChatId(null);
    setMessages([]);
    setResume(null);
    setResumeFileName(null);
    setResumePreviewUrl(null);
    setResumeThumbnailUrl(null);
    setUseResumeProfile(false);
    setIsAccountMenuOpen(false);
    setStatus("Signed out");
  }

  function handleResizeStart(event: PointerEvent<HTMLDivElement>) {
    event.preventDefault();

    const workspace = workspaceRef.current;
    if (!workspace) {
      return;
    }

    const bounds = workspace.getBoundingClientRect();

    function handlePointerMove(moveEvent: globalThis.PointerEvent) {
      const nextWidth = bounds.right - moveEvent.clientX;
      const minWidth = 380;
      const maxWidth = Math.max(minWidth, Math.min(620, bounds.width - 720));
      setJobsWidth(Math.max(minWidth, Math.min(maxWidth, nextWidth)));
    }

    function handlePointerUp() {
      document.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointerup", handlePointerUp);
      document.body.classList.remove("is-resizing");
    }

    document.body.classList.add("is-resizing");
    document.addEventListener("pointermove", handlePointerMove);
    document.addEventListener("pointerup", handlePointerUp);
  }

  if (authLoading && !authSession) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <p className="eyebrow">JobLens</p>
          <h1>Preparing your workspace</h1>
          <p className="muted">Checking your session...</p>
        </section>
      </main>
    );
  }

  if (!authSession) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <div>
            <p className="eyebrow">JobLens</p>
            <h1>{authMode === "signin" ? "Welcome back" : "Create your account"}</h1>
            <p className="muted">
              Sign in to keep your resume, chats, and job matches tied to your account.
            </p>
          </div>

          <form className="auth-form" onSubmit={handleAuthSubmit}>
            {authMode === "signup" ? (
              <label>
                <span>Name</span>
                <input
                  value={authName}
                  onChange={(event) => setAuthName(event.target.value)}
                  placeholder="Tarandeep"
                />
              </label>
            ) : null}
            <label>
              <span>Email</span>
              <input
                type="email"
                value={authEmail}
                onChange={(event) => setAuthEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
            <label>
              <span>Password</span>
              <div className="password-field">
                <input
                  type={showAuthPassword ? "text" : "password"}
                  value={authPassword}
                  onChange={(event) => setAuthPassword(event.target.value)}
                  placeholder="Your password"
                  required
                />
                <button
                  aria-label={showAuthPassword ? "Hide password" : "Show password"}
                  className="password-toggle"
                  type="button"
                  onClick={() => setShowAuthPassword((current) => !current)}
                >
                  {showAuthPassword ? (
                    <svg aria-hidden="true" viewBox="0 0 24 24">
                      <path d="m3 3 18 18" />
                      <path d="M10.6 10.7a2 2 0 0 0 2.7 2.7" />
                      <path d="M9.9 4.2A10.4 10.4 0 0 1 12 4c5.5 0 9 5.5 9 8a7.4 7.4 0 0 1-1.6 2.9" />
                      <path d="M6.4 6.5C4.2 8 3 10.5 3 12c0 2.5 3.5 8 9 8 1.4 0 2.7-.3 3.8-.9" />
                    </svg>
                  ) : (
                    <svg aria-hidden="true" viewBox="0 0 24 24">
                      <path d="M3 12c0-2.5 3.5-8 9-8s9 5.5 9 8-3.5 8-9 8-9-5.5-9-8Z" />
                      <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
                    </svg>
                  )}
                </button>
              </div>
            </label>
            {authNotice ? <p className="auth-notice">{authNotice}</p> : null}
            {authError ? <p className="auth-error">{authError}</p> : null}
            <button type="submit" disabled={authLoading}>
              {authLoading
                ? "Please wait"
                : authMode === "signin"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>

          <button
            className="auth-switch"
            type="button"
            onClick={() => {
              setAuthError(null);
              setAuthNotice(null);
              setAuthMode((current) => (current === "signin" ? "signup" : "signin"));
            }}
          >
            {authMode === "signin"
              ? "Need an account? Create one"
              : "Already have an account? Sign in"}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <section
        className="workspace"
        ref={workspaceRef}
        style={{
          gridTemplateColumns: `190px minmax(520px, 1fr) 6px ${jobsWidth}px`,
        }}
      >
        <aside className="resume-rail">
          <header className="left-header">
            <div className="account-menu" ref={accountMenuRef}>
              <button
                aria-expanded={isAccountMenuOpen}
                className="account-button"
                type="button"
                onClick={() => setIsAccountMenuOpen((current) => !current)}
              >
                <span className="account-avatar">{accountName.charAt(0)}</span>
                <span className="account-copy">
                  <span className="eyebrow">Account</span>
                  <strong>{accountName}</strong>
                </span>
              </button>
              {isAccountMenuOpen ? (
                <div className="account-menu-panel">
                  <button type="button" onClick={() => setStatus("Settings coming soon")}>
                    Settings
                  </button>
                  <button type="button" onClick={handleSignOut}>
                    Log out
                  </button>
                </div>
              ) : null}
            </div>
          </header>

          <section className="resume-panel">
            <div className="panel-heading">
              <h2>Resume</h2>
              <label className="upload-button">
                {uploading ? "Uploading" : "Upload PDF"}
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(event) => handleResumeChange(event.target.files)}
                />
              </label>
            </div>

            {resumeFileName || resumePreviewUrl ? (
              <div className="resume-summary">
                <div
                  className="resume-preview-card"
                  role="button"
                  tabIndex={resumePreviewUrl ? 0 : -1}
                  onClick={() => setIsResumePreviewOpen(true)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setIsResumePreviewOpen(true);
                    }
                  }}
                  aria-disabled={!resumePreviewUrl}
                >
                  {resumeThumbnailUrl ? (
                    <img
                      alt="Resume first page preview"
                      className="resume-preview-image"
                      src={resumeThumbnailUrl}
                    />
                  ) : (
                    <div className="resume-preview-placeholder">PDF</div>
                  )}
                  <div className="resume-preview-meta">
                    <strong>{resumeFileName ?? "Uploaded resume"}</strong>
                    <small>{uploading ? "Parsing resume..." : "Click to preview"}</small>
                  </div>
                </div>
              </div>
            ) : (
              <p className="muted">No resume uploaded for this browser profile.</p>
            )}
          </section>
        </aside>

        <section className="jobs-browser">
          <header className="jobs-browser-header pane-header">
            <div>
              <p className="eyebrow">Database</p>
              <h2>Jobs and internships</h2>
            </div>
            <span className="count-pill">
              {jobsLoading ? "Loading" : `${jobs.length} shown`}
            </span>
          </header>

          <div className="jobs-filters">
            <label className="filter-field filter-search">
              <span>Search</span>
              <input
                value={jobSearch}
                onChange={(event) => setJobSearch(event.target.value)}
                placeholder="Role, company, skill"
              />
            </label>
            <label className="filter-field">
              <span>Mode</span>
              <select
                value={workModeFilter}
                onChange={(event) => setWorkModeFilter(event.target.value)}
              >
                <option value="">Any</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
            </label>
            <label className="filter-field">
              <span>Pay</span>
              <select
                value={paidFilter}
                onChange={(event) => setPaidFilter(event.target.value)}
              >
                <option value="">Any</option>
                <option value="paid">Paid</option>
                <option value="unpaid">Unpaid</option>
              </select>
            </label>
            <div className="filter-field category-filter">
              <span>Category</span>
              <details className="category-menu" ref={categoryMenuRef}>
                <summary>{getCategorySummary()}</summary>
                <div className="category-menu-panel">
                  {CATEGORY_OPTIONS.map((category) => (
                    <label className="category-option" key={category}>
                      <input
                        checked={selectedCategories.includes(category)}
                        type="checkbox"
                        onChange={() => toggleCategory(category)}
                      />
                      <span>{formatDisplayLabel(category)}</span>
                    </label>
                  ))}
                </div>
              </details>
            </div>
          </div>

          <div className="job-list">
            {jobs.length === 0 ? (
              <p className="muted">
                {jobsLoading ? "Loading jobs..." : "No jobs match these filters."}
              </p>
            ) : (
              jobs.map((job, index) => (
                <article className="job-card" key={job.id ?? `${job.title}-${index}`}>
                  <div className="job-card-main">
                    <div>
                      <h3>{job.title ?? "Untitled role"}</h3>
                      <p>{job.org_name ?? "Company not listed"}</p>
                    </div>
                    <button
                      className="job-details-button"
                      type="button"
                      onClick={() => openJobDetails(job)}
                    >
                      Details
                    </button>
                    {job.source_url ? (
                      <a href={job.source_url} target="_blank" rel="noreferrer">
                        Apply <span aria-hidden="true">↗</span>
                      </a>
                    ) : null}
                  </div>
                  <dl>
                    <div>
                      <dt>Location</dt>
                      <dd>{getJobLocation(job)}</dd>
                    </div>
                    <div>
                      <dt>Pay</dt>
                      <dd>{job.stipend_display ?? job.salary_display ?? "Not listed"}</dd>
                    </div>
                    <div>
                      <dt>Duration</dt>
                      <dd>{job.duration_display ?? "Not listed"}</dd>
                    </div>
                    <div>
                      <dt>Source</dt>
                      <dd>{job.source ? formatDisplayLabel(job.source) : "Internshala"}</dd>
                    </div>
                  </dl>
                  {job.skills?.length ? (
                    <div className="tag-row">
                      {job.skills.slice(0, 6).map((skill) => (
                        <span key={skill}>{formatSkillLabel(skill)}</span>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))
            )}
          </div>
        </section>

        <div
          className="splitter"
          role="separator"
          aria-label="Resize jobs panel"
          aria-orientation="vertical"
          onPointerDown={handleResizeStart}
        />

        <section className="chat-panel">
          <header className="chat-header pane-header">
            <div>
              <p className="eyebrow">JobLens Chat</p>
              <h2>Ask about roles, fit, and applications</h2>
            </div>
            <button type="button" onClick={startNewChat}>
              New chat
            </button>
          </header>

          <div className="message-list">
            {messages.length === 0 ? (
              <div className="empty-state">
                <h2>What are you looking for?</h2>
                <p>
                  Try a role, skill, city, stipend, or work mode.
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <article key={message.id} className={`message ${message.role}`}>
                  <span>{message.role === "user" ? "You" : "JobLens"}</span>
                  {message.role === "assistant" &&
                  !message.content &&
                  chatProgress ? (
                    <div className="chat-progress" role="status" aria-live="polite">
                      <span className="progress-dot" />
                      <span>{chatProgress}</span>
                    </div>
                  ) : (
                    <div className="message-markdown">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({ children, href }) => (
                            <a href={href} target="_blank" rel="noreferrer">
                              {children}
                            </a>
                          ),
                        }}
                      >
                        {message.content || "..."}
                      </ReactMarkdown>
                    </div>
                  )}
                </article>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <div className="prompt-box">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="Ask for remote Python internships, React roles in Mumbai..."
                rows={1}
              />
              <div className="prompt-actions">
                <div className="prompt-tools">
                  <label
                    className={`resume-toggle ${!resume ? "disabled" : ""}`}
                    title={
                      resume
                        ? "Use your uploaded resume while searching"
                        : "Upload a resume to enable profile matching"
                    }
                  >
                    <input
                      type="checkbox"
                      checked={useResumeProfile && Boolean(resume)}
                      disabled={!resume}
                      onChange={(event) =>
                        setUseResumeProfile(event.target.checked)
                      }
                    />
                    <span>Use resume</span>
                  </label>
                  <button
                    aria-label="Attach file"
                    className="icon-button"
                    title="Attach file"
                    type="button"
                    onClick={() => setStatus("Chat attachments coming soon")}
                  >
                    <svg aria-hidden="true" viewBox="0 0 24 24">
                      <path d="M21.4 11.6 12.1 20.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.7 9.7a2 2 0 0 1-2.8-2.8l8.9-8.9" />
                    </svg>
                  </button>
                  <button
                    aria-label={
                      voiceState === "listening"
                        ? "Stop voice input"
                        : "Start voice input"
                    }
                    className={`icon-button voice-button ${
                      voiceState === "listening" ? "recording" : ""
                    }`}
                    title={
                      voiceState === "listening"
                        ? "Stop voice input"
                        : "Voice input"
                    }
                    type="button"
                    disabled={voiceState === "transcribing" || isStreaming}
                    onClick={handleVoiceButtonClick}
                  >
                    <svg aria-hidden="true" viewBox="0 0 24 24">
                      <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3Z" />
                      <path d="M19 11a7 7 0 0 1-14 0" />
                      <path d="M12 18v4" />
                      <path d="M8 22h8" />
                    </svg>
                  </button>
                  {voiceState !== "idle" ? (
                    <span className="voice-status" role="status">
                      {voiceState === "listening"
                        ? "Listening..."
                        : "Transcribing..."}
                    </span>
                  ) : voiceError ? (
                    <span className="voice-status error">{voiceError}</span>
                  ) : null}
                </div>
                <button
                  aria-label="Send message"
                  className="send-button"
                  type="submit"
                  disabled={isStreaming || !input.trim()}
                  title="Send message"
                >
                  <svg aria-hidden="true" viewBox="0 0 24 24">
                    <path d="M12 19V5" />
                    <path d="m5 12 7-7 7 7" />
                  </svg>
                </button>
              </div>
            </div>
          </form>
        </section>
      </section>
      {selectedJob ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedJob(null);
            }
          }}
        >
          <section
            aria-label="Job details"
            aria-modal="true"
            className="resume-modal job-modal"
            role="dialog"
          >
            <header className="resume-modal-header">
              <div>
                <p className="eyebrow">Job Details</p>
                <h2>{selectedJob.title ?? "Untitled role"}</h2>
              </div>
              <button
                aria-label="Close job details"
                className="icon-button"
                type="button"
                onClick={() => setSelectedJob(null)}
              >
                <svg aria-hidden="true" viewBox="0 0 24 24">
                  <path d="M18 6 6 18" />
                  <path d="m6 6 12 12" />
                </svg>
              </button>
            </header>

            <div className="job-modal-body">
              {jobDetailsLoading ? <p className="muted">Loading job details...</p> : null}
              {jobDetailsError ? <p className="auth-error">{jobDetailsError}</p> : null}

              <section className="job-detail-summary">
                <div>
                  <span>Company</span>
                  <strong>{selectedJob.org_name ?? "Not given"}</strong>
                </div>
                <div>
                  <span>Location</span>
                  <strong>{getJobDetailLocation(selectedJob)}</strong>
                </div>
                <div>
                  <span>Work mode</span>
                  <strong>
                    {selectedJob.work_mode
                      ? formatDisplayLabel(selectedJob.work_mode)
                      : "Not given"}
                  </strong>
                </div>
                <div>
                  <span>Pay</span>
                  <strong>
                    {selectedJob.stipend_display ??
                      selectedJob.salary_display ??
                      "Not given"}
                  </strong>
                </div>
                <div>
                  <span>Duration</span>
                  <strong>{selectedJob.duration_display ?? "Not given"}</strong>
                </div>
              </section>

              {selectedJob.application_url ? (
                <a
                  className="job-modal-apply"
                  href={selectedJob.application_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Apply <span aria-hidden="true">↗</span>
                </a>
              ) : null}

              <section className="job-detail-section">
                <h3>Description</h3>
                <p>{selectedJob.description || "Not given"}</p>
              </section>

              <section className="job-detail-stack">
                <div className="job-detail-section">
                  <h3>Skills</h3>
                  {selectedJob.skills?.length ? (
                    <div className="tag-row">
                      {selectedJob.skills.map((skill) => (
                        <span key={skill}>{formatSkillLabel(skill)}</span>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">Not given</p>
                  )}
                </div>
                <div className="job-detail-section">
                  <h3>Work Functions</h3>
                  {renderDetailList(selectedJob.work_functions)}
                </div>
                <div className="job-detail-section">
                  <h3>Eligibility</h3>
                  {renderDetailList(selectedJob.eligibility, true)}
                </div>
                <div className="job-detail-section">
                  <h3>Benefits</h3>
                  {renderDetailList(selectedJob.benefits, true)}
                </div>
              </section>
            </div>
          </section>
        </div>
      ) : null}
      {isResumePreviewOpen && resumePreviewUrl ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setIsResumePreviewOpen(false);
            }
          }}
        >
          <section
            aria-label="Resume preview"
            aria-modal="true"
            className="resume-modal"
            role="dialog"
          >
            <header className="resume-modal-header">
              <div>
                <p className="eyebrow">Resume Preview</p>
                <h2>{resumeFileName ?? "Uploaded resume"}</h2>
              </div>
              <button
                aria-label="Close resume preview"
                className="icon-button"
                type="button"
                onClick={() => setIsResumePreviewOpen(false)}
              >
                <svg aria-hidden="true" viewBox="0 0 24 24">
                  <path d="M18 6 6 18" />
                  <path d="m6 6 12 12" />
                </svg>
              </button>
            </header>
            <iframe
              className="resume-frame"
              src={resumePreviewUrl}
              title="Resume PDF preview"
            />
          </section>
        </div>
      ) : null}
    </main>
  );
}
