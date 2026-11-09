import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function Icon({ name, size = 18, ...props }) {
  const paths = {
    activity: <><path d="M3 12h4l3-8 4 16 3-8h4" /></>,
    arrowDown: <><path d="M7 7l10 10M17 7v10H7" /></>,
    arrowUp: <><path d="M7 17 17 7M7 7h10v10" /></>,
    audio: <><path d="M4 10v4m4-8v12m4-16v20m4-16v12m4-8v4" /></>,
    chart: <><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-5 5"/></>,
    check: <><path d="m5 12 4 4L19 6"/></>,
    chevron: <><path d="m6 9 6 6 6-6"/></>,
    help: <><circle cx="12" cy="12" r="9"/><path d="M9.6 9a2.5 2.5 0 0 1 4.8 1c0 1.7-2.4 2-2.4 4m0 3h.01"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    headphones: <><path d="M3 14v-3a9 9 0 0 1 18 0v3"/><rect x="3" y="13" width="4" height="7" rx="2"/><rect x="17" y="13" width="4" height="7" rx="2"/></>,
    dashboard: <><rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="5" rx="1"/><rect x="13" y="10" width="8" height="11" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/></>,
    mic: <><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10a7 7 0 0 0 14 0m-7 7v5m-4 0h8"/></>,
    more: <><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></>,
    pause: <><path d="M8 5v14m8-14v14"/></>,
    play: <><path d="m7 4 14 8-14 8z"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    settings: <><path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.6a8 8 0 0 1-1.4.8l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.5-.8l-1.6.6-1.4-2.4L8 15a8 8 0 0 1 0-1.7l-1.4-1.1L8 9.8l1.7.6a8 8 0 0 1 1.4-.8l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.5.8l1.6-.6 1.4 2.4-1.4 1.1a8 8 0 0 1-.2 1.7Z"/></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
    bag: <><path d="M5 8h14l1 13H4L5 8Z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></>,
    sparkles: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-2-5.8L4 11l6-2.2L12 3Z"/><path d="m19 14 1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2Z"/></>,
    utensils: <><path d="M7 2v7m4-7v7M5 2v5a4 4 0 0 0 8 0V2M9 11v11m8-20v20m0-20c3 2 4 6 4 10h-4"/></>,
    volume: <><path d="M11 5 6 9H3v6h3l5 4V5Zm4 4a5 5 0 0 1 0 6m3-9a9 9 0 0 1 0 12"/></>,
    inbound: <><path d="M7 7l10 10M17 7v10H7"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>;
}

const profiles = [
  { id: 105, name: 'Jordan Lee', role: 'Server', department: 'Front of House', initials: 'JL', tint: 'rose' },
  { id: 106, name: 'Taylor Morgan', role: 'Manager', department: 'Management', initials: 'TM', tint: 'gold' },
  { id: 102, name: 'Elena Rostova', role: 'Shift Lead', department: 'Front of House', initials: 'ER', tint: 'sage' },
  { id: 101, name: 'Dave Miller', role: 'Head Chef', department: 'Kitchen', initials: 'DM', tint: 'blue' },
];

const ACCESS_STORAGE_KEY = 'remi.staff-access.v1';
const accessTools = [
  { id: 'get_menu', label: 'View menu and prices', kind: 'read' },
  { id: 'check_item_availability', label: 'Check item availability', kind: 'read' },
  { id: 'get_order_check', label: 'View order checks', kind: 'read' },
  { id: 'create_order_check', label: 'Submit confirmed guest orders', kind: 'write' },
  { id: 'get_inventory', label: 'View inventory', kind: 'read' },
  { id: 'get_staff_working_now', label: 'View staff working now', kind: 'read' },
  { id: 'get_today_shifts', label: "View today's shifts", kind: 'read' },
  { id: 'get_staff_account_status', label: 'View staff account status', kind: 'read' },
  { id: 'deplete_inventory', label: 'Record inventory depletion', kind: 'write' },
  { id: 'update_shift_schedule', label: 'Edit shift schedules', kind: 'write' },
  { id: 'send_staff_sms_alert', label: 'Send staff SMS alerts via gateway', kind: 'write' },
];
const accessWorkflows = [
  { id: 'staff_assistant', label: 'Staff assistant' },
  { id: 'guest_calls', label: 'Guest calls' },
  { id: 'menu_availability', label: 'Menu & availability' },
  { id: 'insights', label: 'Insights' },
];
const defaultStaffAccess = Object.fromEntries(profiles.map((item) => [item.id, {
  enabled: true,
  workflows: item.role === 'Manager' ? accessWorkflows.map((entry) => entry.id) : ['staff_assistant', 'guest_calls', 'menu_availability'],
  tools: item.role === 'Manager'
    ? accessTools.map((entry) => entry.id)
    : ['get_menu', 'check_item_availability', 'get_order_check', 'create_order_check'],
}]));

function readStaffAccess() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(ACCESS_STORAGE_KEY) || '{}');
    return Object.fromEntries(profiles.map((item) => {
      const value = saved[item.id] || {};
      return [item.id, {
        enabled: value.enabled !== false,
        workflows: Array.isArray(value.workflows) ? value.workflows.filter((id) => accessWorkflows.some((entry) => entry.id === id)) : defaultStaffAccess[item.id].workflows,
        tools: Array.isArray(value.tools) ? value.tools.filter((id) => accessTools.some((entry) => entry.id === id)) : defaultStaffAccess[item.id].tools,
      }];
    }));
  } catch {
    return defaultStaffAccess;
  }
}

function App() {
  const [service, setService] = useState('checking');
  const [health, setHealth] = useState({});
  const [menu, setMenu] = useState([]);
  const [menuStatus, setMenuStatus] = useState('Loading menu…');
  const [capabilities, setCapabilities] = useState({ status: 'loading', tools: [] });
  const [running, setRunning] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [activeNav, setActiveNav] = useState('Overview');
  const [showAll, setShowAll] = useState(false);
  const [listening, setListening] = useState(false);
  const [stopConfirmation, setStopConfirmation] = useState(false);
  const [smsSenderDomain, setSmsSenderDomain] = useState('juniperkitchen.com');
  const [smsFromAddress, setSmsFromAddress] = useState('alerts@juniperkitchen.com');
  const [smsProvider, setSmsProvider] = useState('Resend');
  const [audioError, setAudioError] = useState('');
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [stage, setStage] = useState('sign-in');
  const [profile, setProfile] = useState(null);
  const [scheduleProposal, setScheduleProposal] = useState(false);
  const [scheduleApproved, setScheduleApproved] = useState(false);
  const [settingsSection, setSettingsSection] = useState('Connections');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [voiceProvider, setVoiceProvider] = useState('ElevenLabs');
  const [voiceModel, setVoiceModel] = useState('Eleven Flash v2.5');
  const [voiceStyle, setVoiceStyle] = useState('Warm and reassuring');
  const [voicePreview, setVoicePreview] = useState(false);
  const [personalInstructions, setPersonalInstructions] = useState('');
  const [workplaceInstructions, setWorkplaceInstructions] = useState('Prepare operational drafts for staff review. Require explicit manager approval before any schedule change. Keep guest order conversations in their separate workflow.');
  const [staffAccess, setStaffAccess] = useState(readStaffAccess);
  const [selectedStaffId, setSelectedStaffId] = useState(profiles.find((item) => item.role !== 'Manager')?.id);
  const [daytonaTask, setDaytonaTask] = useState(null);
  const [daytonaBusy, setDaytonaBusy] = useState(false);
  const [daytonaError, setDaytonaError] = useState('');
  const [voiceProcessing, setVoiceProcessing] = useState(false);
  const [remiSpeaking, setRemiSpeaking] = useState(false);
  const [voiceSessionId, setVoiceSessionId] = useState(() => `staff-${crypto.randomUUID()}`);
  const transcriptRef = React.useRef(null);
  const captureRef = React.useRef(null);
  const microphoneActiveRef = React.useRef(false);
  const speakingRef = React.useRef(false);
  const processingRef = React.useRef(false);
  const playbackRef = React.useRef(null);
  const stopConfirmedRef = React.useRef(false);
  const [zoomFactor, setZoomFactor] = useState(1.1);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (transcript) transcript.scrollTop = transcript.scrollHeight;
  }, [messages, scheduleProposal, activeNav, stage]);

  useEffect(() => {
    setVoiceSupported(Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder));
    return () => { microphoneActiveRef.current = false; captureRef.current?.cleanup(); };
  }, []);

  useEffect(() => {
    if (activeNav !== 'Menu & availability') return;
    let active = true;
    setMenuStatus('Loading menu…');
    window.remiWindow?.getMenu?.(profile?.id).then((result) => {
      if (!active) return;
      setMenu(result?.ok ? result.items || [] : []);
      setMenuStatus(result?.ok ? 'Connected to mock POS' : result?.error || 'Menu unavailable');
    });
    return () => { active = false; };
  }, [activeNav, profile?.id]);

  useEffect(() => {
    if (activeNav !== 'Staff assistant' || !profile?.id) return;
    let active = true;
    setCapabilities({ status: 'loading', tools: [] });
    const refresh = async () => {
      try {
        const result = await window.remiWindow?.getCapabilities?.(profile.id);
        if (!active) return;
        setCapabilities(result?.ok ? { status: 'ready', tools: result.tools || [], otherTools: result.other_mcp_tools || [] } : { status: 'error', tools: [], error: result?.error || 'Capabilities unavailable.' });
      } catch {
        if (active) setCapabilities({ status: 'error', tools: [], error: 'Capabilities unavailable.' });
      }
    };
    void refresh();
    const timer = setInterval(refresh, 15000);
    return () => { active = false; clearInterval(timer); };
  }, [activeNav, profile?.id]);

  useEffect(() => {
    window.remiWindow?.getZoomFactor?.().then((value) => {
      if (Number.isFinite(value)) setZoomFactor(value);
    });
    return window.remiWindow?.onZoomChanged?.((value) => {
      if (Number.isFinite(value)) setZoomFactor(value);
    });
  }, []);

  const adjustZoom = (delta) => {
    const next = Math.max(0.8, Math.min(1.5, Math.round((zoomFactor + delta) * 10) / 10));
    setZoomFactor(next);
    window.remiWindow?.setZoomFactor?.(next);
  };

  const renderWindowBar = () => <div className="window-titlebar"><span className="window-title"><img src="/remi-icon.png" alt="" /> Remi</span><div className="window-titlebar-actions"><div className="titlebar-zoom" aria-label="Display zoom"><button aria-label="Zoom out" title="Zoom out (Ctrl/Cmd −)" onClick={()=>adjustZoom(-.1)}>−</button><span>{Math.round(zoomFactor*100)}%</span><button aria-label="Zoom in" title="Zoom in (Ctrl/Cmd +)" onClick={()=>adjustZoom(.1)}>+</button></div><span className="titlebar-divider"/><div className="window-controls"><button aria-label="Minimize window" onClick={() => window.remiWindow?.minimize()}><span className="minimize-glyph" /></button><button aria-label="Maximize window" onClick={() => window.remiWindow?.toggleMaximize()}><span className="maximize-glyph" /></button><button className="close-window" aria-label="Close window" onClick={() => window.remiWindow?.close()}><span className="close-glyph" /></button></div></div></div>;

  useEffect(() => {
    let alive = true;
    const getHealth = () => window.remiWindow?.getDependencyHealth
      ? window.remiWindow.getDependencyHealth()
      : fetch('http://localhost:8000/health/dependencies', { signal: AbortSignal.timeout(3000) })
        .then((response) => { if (!response.ok) throw new Error('Agent health unavailable'); return response.json(); });
    const check = () => getHealth()
      .then((result) => { if (alive) { setHealth(result); setService(result.agent_api?.status === 'online' ? 'online' : 'offline'); } })
      .catch(() => { if (alive) { setService('offline'); setHealth({ agent_api: { status: 'offline' } }); } });
    check();
    const timer = setInterval(check, 15000);
    return () => { alive = false; clearInterval(timer); };
  }, []);

  const startDemo = (prompt = '') => {
    const greeting = `What should we do today ${profile?.role || 'staff'}, ${profile?.name || 'there'}?`;
    setRunning(true);
    setMessages([
      { from: 'remi', text: greeting, time: '00:02' },
      ...(prompt ? [{ from: 'staff', text: prompt, time: '00:08' }] : []),
      ...(prompt ? [{ from: 'remi', text: 'I can help prepare that for staff review. What details should I consider?', time: '00:11' }] : []),
    ]);
    setAudioError('');
    speakingRef.current = true;
    window.remiWindow?.synthesizeSessionGreeting?.(profile?.role || 'staff', profile?.name || 'there')
      .then((result) => {
        if (!result?.ok || !result.audio) return;
        return playElevenLabs(result.audio);
      })
      .catch(() => setAudioError('Could not play the ElevenLabs session greeting. The greeting is available in the transcript.'))
      .finally(() => { speakingRef.current = false; });
    if (stage === 'workspace') void startMicrophone();
  };

  const stopMicrophone = () => {
    microphoneActiveRef.current = false;
    captureRef.current?.cleanup();
    captureRef.current = null;
    setListening(false);
  };

  const interruptPhrase = (text) => /\b(?:hey\s+)?remi\b.{0,32}\b(?:stop|wait|pause|hold on|hold up|quiet)\b/i.test(text)
    || /\b(?:stop|wait|pause|hold on|hold up|quiet)\b.{0,32}\bremi\b/i.test(text);

  const interruptRemi = (text) => {
    const audio = playbackRef.current;
    if (!audio || !speakingRef.current || !interruptPhrase(text)) return false;
    audio.pause();
    audio.currentTime = 0;
    speakingRef.current = false;
    setRemiSpeaking(false);
    const time = new Date().toLocaleTimeString([], { minute: '2-digit', second: '2-digit' });
    setMessages((items) => [...items, { from: 'staff', text, time }, { from: 'remi', text: 'I stopped speaking. I’m listening.', time }]);
    return true;
  };

  const playElevenLabs = async (base64) => {
    if (!base64) return;
    speakingRef.current = true;
    setRemiSpeaking(true);
    try {
      const audio = new Audio(`data:audio/mpeg;base64,${base64}`);
      playbackRef.current = audio;
      await new Promise((resolve) => {
        audio.onended = resolve;
        audio.onerror = resolve;
        audio.onpause = resolve;
        audio.play().catch(resolve);
      });
    } finally {
      playbackRef.current = null;
      speakingRef.current = false;
      setRemiSpeaking(false);
    }
  };

  const processRecognizedText = async (text) => {
    const transcript = text.trim();
    if (!transcript) return;
    if (speakingRef.current) {
      interruptRemi(transcript);
      return;
    }
    const time = new Date().toLocaleTimeString([], { minute: '2-digit', second: '2-digit' });
    if (stopConfirmedRef.current && /\bconfirm stop\b/i.test(transcript)) {
      stopConfirmedRef.current = false;
      setStopConfirmation(false);
      setMessages((items) => [...items, { from: 'staff', text: transcript, time }, { from: 'remi', text: 'Confirmed. I’m stopping microphone capture. Press the microphone button to resume.', time }]);
      const prompt = await window.remiWindow?.synthesizeText?.('Confirmed. I am stopping microphone capture. Press the microphone button to resume.');
      if (prompt?.ok) await playElevenLabs(prompt.audio);
      stopMicrophone();
      return;
    }
    if (stopConfirmedRef.current && /\bcontinue recording\b/i.test(transcript)) {
      stopConfirmedRef.current = false;
      setStopConfirmation(false);
      setMessages((items) => [...items, { from: 'staff', text: transcript, time }, { from: 'remi', text: 'Continuing to listen.', time }]);
      return;
    }
    if (/\b(stop|turn off|disable)\b.{0,24}\b(microphone|mic|recording|listening)\b/i.test(transcript)) {
      stopConfirmedRef.current = true;
      setStopConfirmation(true);
      const promptText = 'I heard a request to stop the microphone. Say confirm stop to stop, or continue recording to keep this session active.';
      setMessages((items) => [...items, { from: 'staff', text: transcript, time }, { from: 'remi', text: promptText, time }]);
      const prompt = await window.remiWindow?.synthesizeText?.(promptText);
      if (prompt?.ok) await playElevenLabs(prompt.audio);
      return;
    }
    if (stopConfirmedRef.current) {
      setMessages((items) => [...items, { from: 'staff', text: transcript, time }, { from: 'remi', text: 'Please say “confirm stop” or “continue recording”.', time }]);
      return;
    }
    if (/schedule/i.test(transcript) && /draft|next week|propos/i.test(transcript)) {
      createScheduleDraft(transcript);
      const speech = await window.remiWindow?.synthesizeText?.('I prepared a sample schedule for your review. A manager can approve the demo draft.');
      if (speech?.ok) await playElevenLabs(speech.audio);
      return;
    }
    if (processingRef.current) return;
    processingRef.current = true;
    setVoiceProcessing(true);
    setMessages((items) => [...items, { from: 'staff', text: transcript, time }]);
    try {
      const result = await window.remiWindow?.processVoiceReply?.({ session_id: voiceSessionId, role: profile?.role || 'Server', user: profile?.name || 'Staff', account_id: profile?.id || 105, transcript });
      if (!result?.ok) throw new Error(result?.error || 'ElevenLabs could not prepare a spoken reply.');
      setMessages((items) => [...items, { from: 'remi', text: result.reply, time }]);
      if (result.audio_error) setAudioError(result.audio_error);
      await playElevenLabs(result.audio_base64);
    } catch (error) {
      setAudioError(error?.message || 'Could not process the voice request.');
    } finally {
      processingRef.current = false;
      setVoiceProcessing(false);
    }
  };

  const startMicrophone = async () => {
    if (microphoneActiveRef.current) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setAudioError('Microphone recording is unavailable in this Electron runtime.');
      setVoiceSupported(false);
      return;
    }
    microphoneActiveRef.current = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      if (!microphoneActiveRef.current) { stream.getTracks().forEach((track) => track.stop()); return; }
      const context = new AudioContext();
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      const samples = new Float32Array(analyser.fftSize);
      let recorder = null;
      let chunks = [];
      let lastSpeech = 0;
      let started = 0;
      let beganDuringPlayback = false;
      let busy = false;
      let frame;
      const cleanup = () => {
        cancelAnimationFrame(frame);
        if (recorder && recorder.state !== 'inactive') { recorder.onstop = null; recorder.stop(); }
        stream.getTracks().forEach((track) => track.stop());
        void context.close();
      };
      captureRef.current = { cleanup };
      setListening(true);
      setAudioError('');
      const tick = () => {
        if (!microphoneActiveRef.current) return;
        analyser.getFloatTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum, sample) => sum + sample * sample, 0) / samples.length);
        const now = performance.now();
        if (!busy && (!processingRef.current || speakingRef.current)) {
          if (rms > 0.018) {
            lastSpeech = now;
            if (!recorder) {
              chunks = [];
              beganDuringPlayback = speakingRef.current;
              recorder = new MediaRecorder(stream);
              recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
              const activeRecorder = recorder;
              const playbackUtterance = beganDuringPlayback;
              recorder.onstop = async () => {
                const blob = new Blob(chunks, { type: activeRecorder.mimeType || 'audio/webm' });
                recorder = null;
                if (!microphoneActiveRef.current || !blob.size) { busy = false; return; }
                try {
                  const bytes = new Uint8Array(await blob.arrayBuffer());
                  let binary = '';
                  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
                  const result = await window.remiWindow.transcribeAudio({ audioBase64: btoa(binary), mimeType: blob.type });
                  if (!result.ok) throw new Error(result.error);
                  // Playback is part of turn processing; allow another utterance
                  // to be recorded while that response is being spoken.
                  busy = false;
                  if (microphoneActiveRef.current && result.transcript) {
                    if (playbackUtterance) interruptRemi(result.transcript);
                    else void processRecognizedText(result.transcript);
                  }
                } catch (error) {
                  busy = false;
                  setAudioError(error?.message || 'Could not transcribe the recording.');
                }
              };
              started = now;
              recorder.start();
            }
          }
          if (recorder && (now - lastSpeech > 1000 || now - started > 20000)) {
            busy = true;
            recorder.stop();
          }
        }
        frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
    } catch {
      microphoneActiveRef.current = false;
      setListening(false);
      setAudioError('Could not start the microphone. Check microphone permissions and try again.');
    }
  };

  const createScheduleDraft = (request = 'Draft the front-of-house shift schedule for next week.') => {
    const wasRunning = running;
    if (!wasRunning) startDemo();
    setRunning(true);
    setScheduleProposal(true);
    setScheduleApproved(false);
    setMessages((items) => [
      ...(wasRunning ? items : [{ from: 'remi', text: `What should we do today ${profile?.role || 'staff'}, ${profile?.name || 'there'}?`, time: '00:02' }]),
      { from: 'staff', text: request, time: '00:08' },
      { from: 'remi', text: 'I’ve prepared a proposed front-of-house schedule for next week. Please review coverage and make any changes before you approve it.', time: '00:16' },
    ]);
  };

  const handleStaffRequest = async (text) => {
    if (stopConfirmedRef.current && /\bconfirm stop\b/i.test(text)) {
      stopConfirmedRef.current = false;
      setStopConfirmation(false);
      setMessages((items) => [...items, { from: 'staff', text, time: 'now' }, { from: 'remi', text: 'Confirmed. Microphone capture has stopped. Press the microphone button to resume.', time: 'now' }]);
      stopMicrophone();
      return;
    }
    if (stopConfirmedRef.current && /\bcontinue recording\b/i.test(text)) {
      stopConfirmedRef.current = false;
      setStopConfirmation(false);
      setMessages((items) => [...items, { from: 'staff', text, time: 'now' }, { from: 'remi', text: 'Continuing to listen.', time: 'now' }]);
      return;
    }
    if (/schedule/i.test(text) && /draft|next week|propos/i.test(text)) {
      createScheduleDraft(text);
      return;
    }
    if (processingRef.current) return;
    processingRef.current = true;
    setVoiceProcessing(true);
    setAudioError('');
    setRunning(true);
    const time = new Date().toLocaleTimeString([], { minute: '2-digit', second: '2-digit' });
    setMessages((items) => [...items, { from: 'staff', text, time }]);
    try {
      const result = await window.remiWindow?.processAgentTurn?.({ session_id: voiceSessionId, transcript: text, account_id: profile?.id || 105, role: profile?.role?.toLowerCase() || 'server' });
      if (!result?.ok) throw new Error(result?.error || 'Agent request failed.');
      setMessages((items) => [...items, { from: 'remi', text: result.reply, time }]);
    } catch (error) {
      setAudioError(error?.message || 'Could not process the staff request.');
    } finally {
      processingRef.current = false;
      setVoiceProcessing(false);
    }
  };

  const approveSchedule = () => {
    setScheduleApproved(true);
    setMessages((items) => [...items, { from: 'remi', text: `Schedule draft approved by ${profile.name}. It has not been sent to 7shifts in this demo.`, time: '00:22' }]);
  };

  const runDaytonaDeliveryReport = async () => {
    setDaytonaError('');
    setDaytonaBusy(true);
    try {
      const started = await window.remiWindow?.startDaytonaReport?.(profile?.id);
      if (!started?.ok) throw new Error(started?.error || 'Could not start the Daytona report.');
      setDaytonaTask({ task_id: started.task_id, status: 'queued', progress: 'Queued for Daytona.' });
      let attempts = 0;
      while (attempts < 60) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        const result = await window.remiWindow?.getDaytonaReport?.(started.task_id);
        setDaytonaTask(result);
        if (['completed', 'failed'].includes(result?.status)) break;
        attempts += 1;
      }
      if (attempts >= 60) setDaytonaError('The report is still running. You can continue working and refresh its status later.');
      if (profile?.role === 'Manager') setActiveNav('Insights');
    } catch (error) {
      setDaytonaError(error?.message || 'The Daytona report could not be started.');
    } finally {
      setDaytonaBusy(false);
    }
  };

  const renderDaytonaReport = () => <section className="panel delivery-report-panel">
    <div className="panel-head"><div><h2>Next delivery planning</h2><p>MarketMan inventory plus year-to-date receiving history, analyzed in Daytona.</p></div><span className={`status-chip ${daytonaTask?.status === 'completed' ? 'active' : ''}`}><i />{daytonaTask?.status || 'Ready'}</span></div>
    <div className="delivery-report-action"><p>Generate a proposed receiving plan for the next delivery. A manager reviews the quantities; Remi will not submit a purchase order.</p><button className="primary-button" onClick={runDaytonaDeliveryReport} disabled={daytonaBusy || profile?.role !== 'Manager'}><Icon name={daytonaBusy ? 'clock' : 'play'} size={15} />{daytonaBusy ? 'Running isolated analysis…' : 'Generate next delivery report'}</button></div>
    {profile?.role !== 'Manager' && <small className="settings-footnote">Sign in as Taylor Morgan (Manager) to run this task.</small>}
    {daytonaTask && <div className="delivery-task-state"><strong>{daytonaTask.status === 'completed' ? 'Report ready' : daytonaTask.status === 'failed' ? 'Task failed' : daytonaTask.progress || 'Task running'}</strong><small>{daytonaTask.progress}</small>{daytonaTask.error && <div className="audio-error">{daytonaTask.error}</div>}{daytonaTask.report && <pre className="delivery-report-output">{daytonaTask.report}</pre>}</div>}
    {daytonaError && <div className="audio-error">{daytonaError}</div>}
  </section>;

  const toggleListening = () => {
    setAudioError('');
    if (microphoneActiveRef.current) {
      stopConfirmedRef.current = false;
      setStopConfirmation(false);
      stopMicrophone();
      return;
    }
    stopConfirmedRef.current = false;
    setStopConfirmation(false);
    startMicrophone();
  };

  const send = (event) => {
    event.preventDefault();
    if (!input.trim()) return;
    const text = input.trim(); setInput('');
    handleStaffRequest(text);
  };

  const nav = [
    { name: 'Overview', icon: 'dashboard' }, { name: 'Staff assistant', icon: 'audio' },
    { name: 'Guest calls', icon: 'headphones' }, { name: 'Menu & availability', icon: 'utensils' },
    { name: 'Insights', icon: 'chart' },
    ...(profile && ['Manager', 'Shift Lead', 'Head Chef'].includes(profile.role) ? [{ name: 'Management', icon: 'shield' }] : []),
  ];

  const chooseProfile = (nextProfile) => { stopMicrophone(); setProfile(nextProfile); setVoiceSessionId(`staff-${crypto.randomUUID()}`); setMessages([]); setScheduleProposal(false); setScheduleApproved(false); setRunning(false); setStage('onboarding'); };
  const signOut = () => { stopMicrophone(); setStage('sign-in'); setProfile(null); setActiveNav('Overview'); setMessages([]); setScheduleProposal(false); setScheduleApproved(false); setRunning(false); };
  const updateStaffAccess = (staffId, update) => {
    setStaffAccess((current) => {
      const next = { ...current, [staffId]: { ...current[staffId], ...update } };
      try { window.localStorage.setItem(ACCESS_STORAGE_KEY, JSON.stringify(next)); } catch { /* Keep the editor usable if storage is unavailable. */ }
      return next;
    });
  };
  const toggleStaffGrant = (staffId, key, grant) => {
    const current = staffAccess[staffId][key];
    updateStaffAccess(staffId, { [key]: current.includes(grant) ? current.filter((item) => item !== grant) : [...current, grant] });
  };
  const roleNotes = {
    Server: ['Use Remi to capture staff tasks and share updates with the team.', 'Guest orders remain a separate server-to-guest workflow.', 'Schedule changes and approvals stay with the manager.'],
    Manager: ['Ask Remi to prepare a front-of-house schedule draft.', 'Review coverage and manually approve proposed schedules.', 'Approved schedules are not sent to 7shifts in this demo.'],
    'Shift Lead': ['Coordinate front-of-house tasks and shift coverage.', 'Prepare requests for a manager to review.', 'Guest-service conversations remain in the separate guest workflow.'],
    'Head Chef': ['Use Remi to coordinate tasks between kitchen and front-of-house staff.', 'Review incoming operational requests and availability.', 'Schedule changes require manager approval.'],
  };

  if (stage !== 'workspace') return <div className="app-shell auth-shell"><main className="main-content">{renderWindowBar()}{stage === 'sign-in' ? <div className="auth-scroll"><section className="signin-page"><div className="signin-brand"><img src="/remi-icon.png" alt=""/><span>remi</span></div><div className="signin-eyebrow">JUNIPER KITCHEN · DEMO WORKSPACE</div><h1>Welcome to Remi</h1><p className="signin-subtitle">Choose a staff profile to explore your personalized workspace.</p><div className="profile-grid">{profiles.map((item) => <button className="profile-card" key={item.id} onClick={() => chooseProfile(item)}><span className={`profile-avatar ${item.tint}`}>{item.initials}</span><span className="profile-copy"><strong>{item.name}</strong><small>{item.role} · {item.department}</small></span><Icon name="arrowUp" size={15}/></button>)}</div><div className="demo-note"><Icon name="shield" size={17}/><span><strong>Demo sign-on</strong><small>These preset profiles show the role-based onboarding flow. No password is needed.</small></span></div></section></div> : <div className="auth-scroll"><section className="onboarding-page"><button className="back-link" onClick={() => setStage('sign-in')}>← All profiles</button><div className="onboarding-avatar"><span className={`profile-avatar ${profile.tint}`}>{profile.initials}</span><div><span className="signin-eyebrow">YOUR FIRST SHIFT</span><h1>Welcome, {profile.name.split(' ')[0]}</h1><p>{profile.role} · {profile.department}</p></div></div><div className="onboarding-card"><div className="onboarding-title"><Icon name="sparkles" size={19}/><div><strong>Your {profile.role.toLowerCase()} workspace is ready</strong><span>A quick guide before you get started.</span></div></div><ul>{roleNotes[profile.role].map((note) => <li key={note}><Icon name="check" size={16}/>{note}</li>)}</ul></div><div className="onboarding-actions"><button className="outline-button" onClick={() => setStage('sign-in')}>Choose another profile</button><button className="primary-button" onClick={() => { setStage('workspace'); window.setTimeout(() => { startDemo(); void startMicrophone(); }, 0); }}>Continue to workspace <Icon name="arrowUp" size={15}/></button></div><p className="access-note">Signed in as <strong>{profile.name}</strong> · mock staff ID {profile.id}</p></section></div>}</main></div>;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><img src="/remi-icon.png" alt="" /></div><span>remi</span><span className="brand-dot">.</span></div>
      <div className="restaurant-switch"><div className="restaurant-avatar">J</div><div className="restaurant-info"><strong>Juniper Kitchen</strong><span>Restaurant workspace</span></div><Icon name="chevron" size={15} /></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{nav.map(({ name, icon, badge }) => <button key={name} className={`nav-item ${activeNav === name ? 'selected' : ''}`} onClick={() => setActiveNav(name)}><Icon name={icon} size={17} strokeWidth={1.8} /><span>{name}</span>{badge && <i>{badge}</i>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="nav-label">PREFERENCES</div><button className={`nav-item ${activeNav === 'Settings' ? 'selected' : ''}`} onClick={() => { setSettingsOpen(true); setSettingsSection('Connections'); }}><Icon name="settings" size={17} /><span>Settings</span></button><button className={`nav-item ${activeNav === 'Help center' ? 'selected' : ''}`} onClick={() => setActiveNav('Help center')}><Icon name="help" size={17} /><span>Help center</span><Icon name="arrowUp" className="external" size={13} /></button><button className="user-card user-switch" onClick={signOut}><span className={`user-avatar ${profile.tint}`}>{profile.initials}</span><span className="user-info"><strong>{profile.name}</strong><span>{profile.role} · Sign out</span></span><Icon name="more" size={18} /></button></div>
    </aside>

    <main className="main-content">
      {renderWindowBar()}
      <header className="topbar"><div className="breadcrumbs">Juniper Kitchen <span>/</span> <strong>{activeNav}</strong></div><div className="top-actions"><button className="icon-button" title="Help" onClick={() => setActiveNav('Help center')}><Icon name="search" size={17} /></button><div className="top-divider" /><button className="account account-button" onClick={signOut}><span className={`mini-avatar ${profile.tint}`}>{profile.initials}</span><span className="account-name">{profile.name}</span><Icon name="chevron" size={14} /></button></div></header>

      <div className="page-scroll"><div className="page-wrap">
        {activeNav === 'Overview' && <>
          <section className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-star"><Icon name="sparkles" size={13} /></span> REMI OPERATIONS</div><h1>Automation overview</h1><p>Monitor staff-task automation, service connectors, and provider readiness.</p></div><button className="primary-button open-call-button" onClick={() => setActiveNav('Staff assistant')}><Icon name="audio" size={15}/> Open staff assistant</button></section>
          <section className="health-grid">{[
            { key: 'agent_api', title: 'Remi API', subtitle: 'FastAPI agent', icon: 'activity' },
            { key: 'mock_pos', title: 'Mock integrations', subtitle: 'POS · 7shifts · MarketMan', icon: 'dashboard' },
            { key: 'elevenlabs', title: 'ElevenLabs', subtitle: 'Speech provider', icon: 'audio' },
            { key: 'daytona', title: 'Daytona', subtitle: 'Isolated execution', icon: 'shield' },
          ].map((item) => { const state = health[item.key]?.status || (service === 'offline' ? 'offline' : 'checking'); const label = state === 'online' ? 'Connected' : state === 'offline' ? 'Offline' : state === 'unknown' ? 'API unavailable' : state === 'configured_unverified' ? 'Configured · unverified' : state === 'not_configured' ? 'Not configured' : 'Checking'; return <article className="panel health-card" key={item.key}><div className="health-card-top"><span className="health-icon"><Icon name={item.icon} size={18}/></span><span className={`health-status ${state}` }><i/>{label}</span></div><h2>{item.title}</h2><p>{item.subtitle}</p><small>{health[item.key]?.detail || (service === 'offline' ? 'Start the Remi API to check this service.' : 'Waiting for service status.')}</small></article>; })}</section>
          <div className="ops-grid"><section className="panel connectors-panel"><div className="panel-head"><div><h2>Backend connectors</h2><p>Restaurant systems available to the agent runtime.</p></div><span className="section-kicker">MOCK ENVIRONMENT</span></div><div className="connector-list">{[
            ['Oracle POS', 'Menu lookup and order checks', health.mock_pos?.status || 'checking'],
            ['7shifts', 'Staff accounts and shift status', health.mock_pos?.status || 'checking'],
            ['MarketMan', 'Inventory and item availability', health.mock_pos?.status || 'checking'],
          ].map(([name, detail, state]) => <div className="connector-row" key={name}><span className="connector-mark"><Icon name={name === 'Oracle POS' ? 'bag' : name === '7shifts' ? 'clock' : 'activity'} size={17}/></span><span className="connector-text"><strong>{name}</strong><small>{detail}</small></span><span className={`connector-state ${state}` }><i/>{state === 'online' ? 'Reachable' : state === 'offline' ? 'Unavailable' : 'Checking'}</span></div>)}</div><div className="connector-footnote">All three mock connectors run through the local integrations service.</div></section>
            <section className="panel automation-panel"><div className="panel-head"><div><h2>Front-of-house automation</h2><p>Staff requests Remi can prepare for review.</p></div><Icon name="sparkles" className="quick-spark" size={19}/></div><button className="automation-row task-action" onClick={() => { setActiveNav('Staff assistant'); createScheduleDraft(); }}><span className="automation-icon"><Icon name="clock" size={16}/></span><span><strong>Draft next week’s FOH schedule</strong><small>Prepare coverage for manager review and manual approval.</small></span><b className="task-tag">REVIEW</b></button><div className="automation-row"><span className="automation-icon"><Icon name="activity" size={16}/></span><span><strong>Staff task coordination</strong><small>Capture requests and route them to the right role.</small></span><b className="task-tag ready">PLANNED</b></div><div className="automation-row"><span className="automation-icon"><Icon name="headphones" size={16}/></span><span><strong>Guest service</strong><small>Separate server-to-guest communication workflow.</small></span><b className="task-tag ready">SEPARATE</b></div><div className="integration-note">Schedule drafting and approval are a local demo flow; no schedule is sent to 7shifts.</div></section></div>
          <footer className="page-footer"><span>© 2025 Remi AI</span><span><span className={`footer-live ${service === 'offline' ? 'offline' : ''}`} /> {service === 'online' ? 'Agent API responding' : service === 'offline' ? 'Agent API unreachable' : 'Checking agent API'} <i>·</i> Demo workspace</span></footer>
        </>}
        {activeNav === 'Staff assistant' && <section className="subpage call-page"><div className="subpage-heading"><span className="section-kicker">STAFF OPERATIONS</span><h1>Staff task assistant</h1><p>Talk through an operational task, review the transcript and inspect what Remi has in context.</p></div><div className="live-call-layout"><section className="panel transcript-panel"><div className="panel-head"><div><h2>Staff conversation</h2><p>Private staff-to-Remi task session.</p></div><span className={`status-chip ${running ? 'active' : ''}`}><i/>{running ? 'Session active' : 'Ready'}</span></div><div className="staff-quick-actions"><button onClick={() => createScheduleDraft()}>Draft next week’s FOH schedule</button><button onClick={() => handleStaffRequest('Who is working now?')}>Check today’s coverage</button></div><div className="transcript-scroll" ref={transcriptRef}>{messages.length ? <>{messages.map((message,index)=><article className={`transcript-turn ${message.from}`} key={`${message.time}-${index}`}><span className="transcript-avatar">{message.from==='remi'?<Icon name="audio" size={14}/>:profile.initials}</span><div className="transcript-content"><div><strong>{message.from==='remi'?'Remi':profile.name}</strong><time>{message.time}</time></div><p>{message.text}</p></div></article>)}{scheduleProposal && <section className="schedule-proposal"><div className="proposal-heading"><div><span className="section-kicker">DRAFT · NEXT WEEK</span><h3>Front-of-house schedule</h3></div><span className={`table-status ${scheduleApproved?'good':'neutral'}`}>{scheduleApproved?'Approved':'Needs manager approval'}</span></div><p className="proposal-summary">Proposed coverage for the service team. Review shift assignments before approving.</p><div className="schedule-rows">{[['Mon','Jordan Lee','11:00–7:00','Floor'],['Tue','Elena Rostova','11:00–7:00','Shift lead'],['Wed','Marcus Vance','4:00–11:30','Bar'],['Thu','Jordan Lee','11:00–7:00','Floor'],['Fri','Elena Rostova','3:00–11:00','Floor'],['Sat','Marcus Vance','4:00–11:30','Bar'],['Sun','Jordan Lee','11:00–6:00','Floor']].map((shift)=> <div className="schedule-row" key={`${shift[0]}-${shift[1]}`}><b>{shift[0]}</b><span>{shift[1]}</span><span>{shift[2]}</span><small>{shift[3]}</small></div>)}</div>{profile.role==='Manager' ? <button className="primary-button approve-schedule" disabled={scheduleApproved} onClick={approveSchedule}><Icon name="check" size={15}/>{scheduleApproved?'Approved by manager':'Approve schedule draft'}</button> : <div className="approval-note"><Icon name="shield" size={15}/> Only a Manager profile can approve this schedule.</div>}<small className="proposal-disclaimer">Demo proposal only. Approval changes the demo status; it does not write to 7shifts.</small></section>}</> : <div className="transcript-empty"><span className="transcript-empty-icon"><Icon name="audio" size={20}/></span><strong>Start a staff task</strong><p>Ask Remi to draft next week’s schedule, review shift coverage or help coordinate a front-of-house task.</p><button className="primary-button" onClick={()=>createScheduleDraft()}><Icon name="play" size={14}/> Try schedule drafting</button></div>}</div><form className="composer transcript-composer" onSubmit={send}><button type="button" className={`mic-button ${listening?'listening':''}`} onClick={toggleListening} aria-label={listening?'Stop microphone now':'Start microphone'} title={listening?'Stop microphone now (manual stop bypasses confirmation)':'Start microphone'}><Icon name="mic" size={17}/></button><input value={input} onChange={(event)=>setInput(event.target.value)} placeholder={remiSpeaking?'Say “Remi, stop” to interrupt…':stopConfirmation?'Say “confirm stop” or “continue recording”…':voiceProcessing?'Preparing spoken reply…':listening?'Listening continuously… speak a staff request':'Microphone stopped · press to resume'}/><span className="demo-hint">{remiSpeaking?'SAY REMI TO INTERRUPT':stopConfirmation?'CONFIRM':voiceProcessing?'PROCESSING':listening?'LIVE MIC':voiceSupported?'MIC OFF':'NO MIC'}</span><button className="send-button" type="submit"><Icon name="arrowUp" size={17}/></button></form>{audioError&&<div className="audio-error">{audioError}</div>}</section><aside className="panel agent-context"><div className="panel-head"><div><h2>Agent context</h2><p>Staff, task and approval rules for this session.</p></div><span className="context-live"><i/> ACTIVE</span></div><div className="context-block"><span className="context-label">WORKSPACE</span><strong>Juniper Kitchen</strong><small>Front-of-house operations</small></div><div className="context-block"><span className="context-label">SIGNED-IN STAFF</span><strong>{profile.name} · {profile.role}</strong><small>Profile #{profile.id} · {profile.department}</small></div><div className="context-block"><span className="context-label">CURRENT REQUEST</span><p>{messages.filter((m)=>m.from==='staff').at(-1)?.text || (listening?'Listening for a staff request…':'Waiting for a staff task.')}</p></div><div className="context-block"><span className="context-label">WORKING RULES</span><ul><li>Prepare drafts for staff review before changing operational records.</li><li>Shift schedules require explicit manual approval from a manager.</li><li>Guest-facing server conversations remain a separate workflow.</li></ul></div><div className="context-block tools-block"><span className="context-label">MCP TOOLS FOR THIS PROFILE</span>{capabilities.status === 'loading' ? <small>Checking profile access…</small> : capabilities.status === 'error' ? <small>{capabilities.error}</small> : <><small>Available to the staff assistant</small><div className="tool-chips">{capabilities.tools.map((tool) => <span key={tool}>{tool}</span>)}</div>{capabilities.otherTools.length > 0 && <><small>Available through other MCP workflows</small><div className="tool-chips">{capabilities.otherTools.map((tool) => <span key={tool}>{tool}</span>)}</div></>}<small>Other workflows are not yet connected to the staff assistant.</small></>}</div><button className="outline-button end-call-button" onClick={()=>{stopMicrophone();setRunning(false);setStopConfirmation(false);stopConfirmedRef.current=false;window.remiRecognition?.stop();}}>End staff session</button></aside></div></section>}
                {activeNav === 'Guest calls' && <section className="subpage"><div className="subpage-heading"><span className="section-kicker">GUEST INTERACTIONS</span><h1>Guest calls</h1><p>Separate server-to-guest interactions and service outcomes.</p></div><div className="panel data-panel"><div className="table-toolbar"><strong>Recent calls</strong><span>Today · 6 calls</span></div><table><thead><tr><th>GUEST</th><th>REASON</th><th>OUTCOME</th><th>DURATION</th><th>TIME</th></tr></thead><tbody>{[['Guest 1042','Takeout order','Order completed','2:14','2m ago'],['Guest 1041','Menu question','Answered','1:08','18m ago'],['Guest 1040','Reservation','Transferred to staff','3:42','41m ago'],['Guest 1039','Takeout order','Order completed','2:56','1h ago'],['Guest 1038','Hours & location','Answered','0:48','2h ago']].map((row) => <tr key={row[0]}>{row.map((item, index) => <td key={item}>{index === 2 ? <span className={`table-status ${item.includes('completed') ? 'good' : item === 'Answered' ? 'neutral' : 'warm'}`}>{item}</span> : item}</td>)}</tr>)}</tbody></table></div></section>}
        {activeNav === 'Menu & availability' && <section className="subpage"><div className="subpage-heading"><span className="section-kicker">RESTAURANT SETUP</span><h1>Menu & availability</h1><p>See the sample POS menu and current mock availability.</p></div><div className="panel data-panel"><div className="table-toolbar"><strong>Juniper Kitchen menu</strong><span>{menuStatus}</span></div><table><thead><tr><th>ICON</th><th>ITEM</th><th>CATEGORY</th><th>PRICE</th><th>AVAILABILITY</th></tr></thead><tbody>{menu.map((item) => <tr key={item.item_id}><td><img className="menu-category-icon" src={`.${item.icon_url}`} alt={`${item.category} category icon`} /></td><td className="menu-item-name">{item.name}</td><td>{item.category}</td><td>${Number(item.price).toFixed(2)}</td><td><span className="table-status neutral">Not checked</span></td></tr>)}</tbody></table></div><div className="info-banner"><Icon name="help" size={18}/><span>Menu updates are read-only in this demo. Menu prices come from the mock POS. Availability is not checked on this page.</span></div></section>}
        {activeNav === 'Insights' && (
          <section className="subpage">
            <div className="subpage-heading"><span className="section-kicker">TASK AUTOMATION</span><h1>Insights</h1><p>Operational workflow measurements for the Remi demonstration.</p></div>
            {renderDaytonaReport()}
            <div className="insight-grid">
              <div className="panel insight-card"><span>Schedule drafts</span><strong>3</strong><small>Sample proposals this week</small></div>
              <div className="panel insight-card"><span>Awaiting manager review</span><strong>1</strong><small>Manual approval required</small></div>
              <div className="panel insight-card"><span>Staff task queue</span><strong>2 open</strong><small>Demo workflow snapshot</small><div className="insight-stars">Front of house</div></div>
            </div>
            <div className="info-banner"><Icon name="help" size={18}/><span>These are sample operational indicators, not measured production results.</span></div>
          </section>
        )}
        {activeNav === 'Management' && <section className="subpage"><div className="subpage-heading"><span className="section-kicker">ELEVATED ACCESS</span><h1>Workplace management</h1><p>Review staff roles and configure their Remi workflows and MCP tool access.</p></div>{['Manager','Shift Lead','Head Chef'].includes(profile.role)?<><div className="management-summary"><article className="panel management-stat"><span>WORKSPACE ROLE</span><strong>{profile.role}</strong><small>{profile.name} · Juniper Kitchen</small></article><article className="panel management-stat"><span>STAFF PROFILES</span><strong>{profiles.length}</strong><small>Demo staff directory</small></article><article className="panel management-stat"><span>ACCESS POLICIES</span><strong>Local demo</strong><small>Not enforced by backend</small></article></div><div className="panel management-panel"><div className="panel-head"><div><h2>Staff and access</h2><p>Configure who can use each Remi workflow and MCP tool.</p></div><span className="section-kicker">{profile.role.toUpperCase()}</span></div><div className="management-staff-list">{profiles.map((member)=>{const access=staffAccess[member.id];const editable=profile.role==='Manager'&&member.id!==profile.id;return <article className="management-staff-row" key={member.id}><span className={`profile-avatar ${member.tint}`}>{member.initials}</span><div className="management-staff-person"><strong>{member.name}</strong><small>{member.role} · {member.department} · {access.enabled?'Enabled':'Disabled'}</small></div><div className="management-access-summary"><span>{access.workflows.length} workflows</span><span>{access.tools.length} tools</span></div>{editable?<button className="outline-button" onClick={()=>{setSelectedStaffId(member.id);setSettingsSection('Staff access');setSettingsOpen(true);}}>Manage access</button>:<span className="management-self">{member.id===profile.id?'You':profile.role==='Manager'?'Owner access':'View only'}</span>}</article>})}</div></div><div className="settings-note"><strong>Prototype controls:</strong> access selections persist in this desktop profile's local storage only. Backend MCP permissions are still fixed by role. Production access management needs authenticated server-side policy checks and audit history.</div></>:<div className="settings-note">This profile does not have elevated access to workplace management.</div>}</section>}
        {activeNav === 'Settings' && <section className="subpage"><div className="subpage-heading"><span className="section-kicker">WORKSPACE</span><h1>Settings</h1><p>Configure connections, voice, sandbox execution and agent guidance.</p></div><div className="settings-grid"><button className="panel settings-card settings-launch" onClick={()=>{setSettingsSection('Display');setSettingsOpen(true);}}><span className="settings-launch-icon"><Icon name="activity"/></span><h2>Connections</h2><p>API endpoints, provider readiness and integrations.</p></button><button className="panel settings-card settings-launch" onClick={()=>{setSettingsSection('Voice agent');setSettingsOpen(true);}}><span className="settings-launch-icon"><Icon name="audio"/></span><h2>Voice agent</h2><p>Provider, model, voice style and spoken demo.</p></button><button className="panel settings-card settings-launch" onClick={()=>{setSettingsSection('Daytona');setSettingsOpen(true);}}><span className="settings-launch-icon"><Icon name="shield"/></span><h2>Sandbox settings</h2><p>Daytona execution and runtime guardrails.</p></button><button className="panel settings-card settings-launch" onClick={()=>{setSettingsSection('Agent instructions');setSettingsOpen(true);}}><span className="settings-launch-icon"><Icon name="sparkles"/></span><h2>Agent instructions</h2><p>Your personal preferences for Remi.</p></button><button className="panel settings-card settings-launch" onClick={()=>{setSettingsSection('Workplace instructions');setSettingsOpen(true);}}><span className="settings-launch-icon"><Icon name="utensils"/></span><h2>Workplace instructions</h2><p>Shared restaurant operating rules and system guidance.</p></button><div className="panel settings-card"><h2>Signed-in profile</h2><div className="profile-summary"><span className={`profile-avatar ${profile.tint}`}>{profile.initials}</span><div><strong>{profile.name}</strong><small>{profile.role} · {profile.department}</small></div></div><button className="outline-button" onClick={signOut}>Switch profile</button></div></div></section>}
        {settingsOpen && <div className="settings-overlay" role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)setSettingsOpen(false);}}><section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title"><header className="settings-modal-head"><div><span className="section-kicker">REMI CONFIGURATION</span><h2 id="settings-title">Workspace settings</h2></div><button className="settings-close" aria-label="Close settings" onClick={()=>setSettingsOpen(false)}>×</button></header><div className="settings-modal-body"><nav className="settings-tabs">{['Display','Connections','Voice agent','Staff SMS & Alerts','Daytona','Agent instructions','Workplace instructions','Staff access'].map((item)=><button key={item} className={settingsSection===item?'selected':''} onClick={()=>setSettingsSection(item)}>{item}</button>)}</nav><div className="settings-editor">
          {settingsSection==='Display'&&<><h3>Display size</h3><p>Adjust interface scale. Keyboard shortcuts also work: Ctrl/Cmd +, Ctrl/Cmd -, and Ctrl/Cmd 0.</p><div className="zoom-control"><button className="outline-button" onClick={()=>{const value=Math.max(.8,Math.round((zoomFactor-.1)*10)/10);setZoomFactor(value);window.remiWindow?.setZoomFactor?.(value);}}>−</button><strong>{Math.round(zoomFactor*100)}%</strong><button className="outline-button" onClick={()=>{const value=Math.min(1.5,Math.round((zoomFactor+.1)*10)/10);setZoomFactor(value);window.remiWindow?.setZoomFactor?.(value);}}>+</button><button className="text-link" onClick={()=>{setZoomFactor(1);window.remiWindow?.setZoomFactor?.(1);}}>Reset</button></div><div className="zoom-presets">{[['Compact',.9],['Default',1],['Comfortable',1.1],['Large',1.25]].map(([name,value])=><button className={Math.abs(zoomFactor-value)<.02?'selected':''} key={name} onClick={()=>{setZoomFactor(value);window.remiWindow?.setZoomFactor?.(value);}}>{name}</button>)}</div><small className="settings-footnote">Supported range: 80%–150%. Current zoom is {Math.round(zoomFactor*100)}%.</small></>}
          {settingsSection==='Connections'&&<><h3>Connections & API endpoints</h3><p>Service URLs are local MVP settings. Secrets belong in the API service environment, never in the desktop client.</p><div className="connection-line"><span><strong>Remi Agent API</strong><small>http://localhost:8000 · voice greeting & health</small></span><b className={service==='online'?'service-ok':'service-off'}>{service==='online'?'Reachable':'Unavailable'}</b></div><div className="connection-line"><span><strong>Mock restaurant connectors</strong><small>Oracle POS, 7shifts and MarketMan · {health.mock_pos?.detail||'MOCK_POS_BASE_URL'}</small></span><b className={health.mock_pos?.status==='online'?'service-ok':'service-demo'}>{health.mock_pos?.status==='online'?'Reachable':'Mock'}</b></div><div className="connection-line"><span><strong>ElevenLabs</strong><small>{health.elevenlabs?.detail||'Set ELEVENLABS_API_KEY on the agent service.'}</small></span><b className={health.elevenlabs?.status==='configured_unverified'?'service-demo':'service-off'}>{health.elevenlabs?.status==='configured_unverified'?'Configured':'Not configured'}</b></div><div className="connection-line"><span><strong>Daytona</strong><small>{health.daytona?.detail||'Set DAYTONA_API_KEY on the agent service.'}</small></span><b className={health.daytona?.status==='configured_unverified'?'service-demo':'service-off'}>{health.daytona?.status==='configured_unverified'?'Configured':'Not configured'}</b></div><div className="settings-note">Endpoint and credential editing is intentionally server-side for this single-restaurant MVP. Configure them in the project .env; this panel reports connection status.</div></>}
          {settingsSection==='Voice agent'&&<><h3>Voice & personality</h3><p>Choose the provider and style for spoken assistant responses. Preview uses the configured ElevenLabs session greeting.</p><label className="field-label">Speech provider<select value={voiceProvider} onChange={e=>setVoiceProvider(e.target.value)}><option>ElevenLabs</option><option disabled>System voice (coming later)</option></select></label><label className="field-label">Model<select value={voiceModel} onChange={e=>setVoiceModel(e.target.value)}><option>Eleven Flash v2.5</option><option disabled>Other ElevenLabs models (coming later)</option></select></label><label className="field-label">Personality<select value={voiceStyle} onChange={e=>setVoiceStyle(e.target.value)}><option>Warm and reassuring</option><option>Concise and efficient</option><option>Upbeat and friendly</option></select></label><button className="primary-button" disabled={voicePreview} onClick={async()=>{setVoicePreview(true);try{const result=await window.remiWindow?.synthesizeSessionGreeting?.(profile.role,profile.name);if(result?.ok){const audio=new Audio(`data:audio/mpeg;base64,${result.audio}`);await audio.play();}else setAudioError('ElevenLabs is not configured or could not return the preview.');}catch{setAudioError('Could not play the voice preview.');}finally{setVoicePreview(false);}}}><Icon name="play" size={14}/>{voicePreview?'Preparing preview…':'Preview greeting'}</button>{audioError&&<div className="audio-error settings-audio-error">{audioError}</div>}<small className="settings-footnote">Voice style is a UI preference in this demo; model and personality controls are not yet persisted or injected into agent prompts.</small></>}
          {settingsSection==='Staff SMS & Alerts'&&<>
            <h3>Staff SMS & Email-to-SMS Gateway</h3>
            <p>Configure how text messages appear on employees' phones when Remi contacts them about shift coverage or rush hours.</p>
            <label className="field-label">Delivery Provider
              <select value={smsProvider} onChange={e=>setSmsProvider(e.target.value)}>
                <option>Resend REST API (Recommended)</option>
                <option>Standard SMTP (Gmail / Custom)</option>
                <option>Local Mock Simulator</option>
              </select>
            </label>
            <label className="field-label">Verified Sender Address
              <input type="text" value={smsFromAddress} onChange={e=>setSmsFromAddress(e.target.value)} placeholder="alerts@your-restaurant.com" />
            </label>
            <div className="settings-note">
              <strong>How it looks to recipients:</strong> Texts arrive in their mobile SMS/iMessage inbox from <code>{smsFromAddress}</code>. Staff replies are routed back to this address.
            </div>
          </>}
          {settingsSection==='Daytona'&&<><h3>Sandbox settings</h3><p>Run long inventory analysis in an isolated Daytona sandbox. Regular POS requests stay on the direct service path.</p><div className="connection-line"><span><strong>Daytona credentials</strong><small>{health.daytona?.detail||'Set DAYTONA_API_KEY on the Remi Agent API environment.'}</small></span><b className={health.daytona?.status==='configured_unverified'?'service-demo':'service-off'}>{health.daytona?.status==='configured_unverified'?'Ready to verify':'Not configured'}</b></div><div className="settings-note">The demo task queries read-only mock MarketMan inventory and illustrative year-to-date receiving records, then produces a manager-review report. It does not create a purchase order. Runtime is configured on the backend and capped at 180 seconds.</div><small className="settings-footnote">Daytona host, API key and optional target are configured on the backend using DAYTONA_API_KEY, DAYTONA_API_URL and DAYTONA_TARGET.</small></>}
          {settingsSection==='Agent instructions'&&<><h3>Your agent instructions</h3><p>Personal preferences for this signed-in staff profile.</p><label className="field-label">Personal guidance<textarea rows="7" maxLength="2000" value={personalInstructions} onChange={e=>setPersonalInstructions(e.target.value)} placeholder="For example: Keep updates brief and flag staffing gaps before proposing changes."/></label><small className="settings-footnote">Saved in this window for the demo; currently not sent to the agent service.</small></>}
          {settingsSection==='Workplace instructions'&&<><h3>Workplace instructions</h3><p>Shared rules for Remi at Juniper Kitchen. These form workplace-level system guidance.</p><label className="field-label">Workplace operating rules<textarea rows="8" maxLength="4000" value={workplaceInstructions} onChange={e=>setWorkplaceInstructions(e.target.value)}/></label><small className="settings-footnote">Only trusted managers should edit shared instructions. This demo stores the text in memory and does not yet inject it into the backend system prompt.</small></>}
        </div></div><footer className="settings-modal-foot"><span>Settings changes are demo-local unless stated otherwise.</span><button className="outline-button" onClick={()=>setSettingsOpen(false)}>Done</button></footer></section></div>}
        {activeNav === 'Help center' && <section className="subpage"><div className="subpage-heading"><span className="section-kicker">SUPPORT</span><h1>Help center</h1><p>Quick answers for the Remi demonstration workspace.</p></div><div className="help-grid">{[['Getting started','Choose a staff profile, review the role guide, then open the workspace.'],['Using voice input','Select the microphone and allow access when your system asks. Microphone audio is transcribed by ElevenLabs after a pause.'],['Order safety','Remi should read the complete order back and receive guest confirmation before submission.'],['Demo limitations','Voice uses ElevenLabs and selected read-only restaurant tools; schedule approval remains a local demo.']].map(([title,body])=><article className="panel help-card" key={title}><Icon name="help" size={19}/><h2>{title}</h2><p>{body}</p></article>)}</div></section>}
      </div></div>
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
