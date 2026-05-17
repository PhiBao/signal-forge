"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAccount, useConnect, useDisconnect, useSignTypedData, useWriteContract, useReadContract } from "wagmi";
import { injected } from "wagmi/connectors";
import { parseUnits, formatUnits } from "viem";

const API = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const USDC_ADDRESS = "0x3600000000000000000000000000000000000000";

const USDC_ABI = [
  { name: "balanceOf", type: "function", stateMutability: "view", inputs: [{ name: "account", type: "address" }], outputs: [{ name: "", type: "uint256" }] },
  { name: "transfer", type: "function", stateMutability: "nonpayable", inputs: [{ name: "to", type: "address" }, { name: "amount", type: "uint256" }], outputs: [{ name: "", type: "bool" }] },
] as const;

function fetchJson(url: string) {
  return fetch(`${API}${url}`).then((r) => r.json());
}

function postJson(url: string, body?: unknown) {
  return fetch(`${API}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  }).then((r) => r.json());
}

function putJson(url: string, body: unknown) {
  return fetch(`${API}${url}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => r.json());
}

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [showHelp, setShowHelp] = useState(true);
  const [showStack, setShowStack] = useState(false);
  const [showSubscriptions, setShowSubscriptions] = useState(false);
  const [expandedSignal, setExpandedSignal] = useState<number | null>(null);
  const [lastCycleResult, setLastCycleResult] = useState<any>(null);
  const [subAddress, setSubAddress] = useState("");
  const [showTerminal, setShowTerminal] = useState(false);
  const [agentLogs, setAgentLogs] = useState<string[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [showDepositPrompt, setShowDepositPrompt] = useState(false);

  const { address, isConnected } = useAccount();
  const { connect } = useConnect();
  const { disconnect } = useDisconnect();

  useEffect(() => {
    setMounted(true);
    const dismissed = localStorage.getItem("signalforge-help-dismissed");
    if (dismissed) setShowHelp(false);
  }, []);

  const addLog = (msg: string) => {
    const timestamp = new Date().toLocaleTimeString("en-US", { hour12: false });
    setAgentLogs(prev => [...prev.slice(-50), `[${timestamp}] ${msg}`]);
  };

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ["status"],
    queryFn: () => fetchJson("/api/agent/status"),
    refetchInterval: (q) => (q.state.data?.is_running ? 5000 : false),
  });

  const { data: signals } = useQuery({
    queryKey: ["signals"],
    queryFn: () => fetchJson("/api/signals"),
    refetchInterval: 10000,
  });

  const { data: config, refetch: refetchConfig } = useQuery({
    queryKey: ["config"],
    queryFn: () => fetchJson("/api/config"),
  });

  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => fetchJson("/api/portfolio"),
    refetchInterval: 10000,
  });

  const { data: trades } = useQuery({
    queryKey: ["trades"],
    queryFn: () => fetchJson("/api/trades?limit=20"),
    refetchInterval: 10000,
  });

  const { data: stack } = useQuery({
    queryKey: ["stack"],
    queryFn: () => fetchJson("/api/circle-stack"),
  });

  const { data: subStats } = useQuery({
    queryKey: ["sub-stats"],
    queryFn: () => fetchJson("/api/subscriptions/stats"),
    refetchInterval: 10000,
  });

  const { data: subscriptions, refetch: refetchSubscriptions } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => fetchJson("/api/subscriptions"),
    refetchInterval: 10000,
    enabled: showSubscriptions,
  });

  const { data: backendLogs } = useQuery({
    queryKey: ["logs"],
    queryFn: () => fetchJson("/api/logs?limit=30"),
    refetchInterval: showTerminal ? 2000 : false,
    enabled: showTerminal,
  });

  useEffect(() => {
    if (backendLogs && backendLogs.length > 0) {
      setAgentLogs(backendLogs);
    }
  }, [backendLogs]);

  const startMutation = useMutation({
    mutationFn: () => postJson("/api/agent/start"),
    onSuccess: () => {
      refetchStatus();
      addLog("AUTO-RUN started — agent will scan every 15min");
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => postJson("/api/agent/stop"),
    onSuccess: () => {
      refetchStatus();
      addLog("AUTO-RUN stopped");
    },
  });

  const cycleMutation = useMutation({
    mutationFn: async () => {
      setIsScanning(true);
      addLog("Initializing scan cycle...");
      await new Promise(r => setTimeout(r, 300));
      addLog("Fetching 50 markets from Polymarket Gamma API...");
      await new Promise(r => setTimeout(r, 500));
      addLog("Fetching news context for market analysis...");
      await new Promise(r => setTimeout(r, 400));
      addLog("Sending markets to DGrid AI for analysis...");
      await new Promise(r => setTimeout(r, 800));
      addLog("Analyzing edge vs market-implied probabilities...");
      await new Promise(r => setTimeout(r, 300));
      addLog("Applying Kelly Criterion position sizing...");
      await new Promise(r => setTimeout(r, 200));
      const result = await postJson("/api/cycle");
      addLog(`Found ${result.signals_found} signals — executing top 3...`);
      await new Promise(r => setTimeout(r, 400));
      addLog("Anchoring reasoning traces on Arc blockchain...");
      await new Promise(r => setTimeout(r, 300));
      addLog("USDC settlement transfers initiated...");
      await new Promise(r => setTimeout(r, 200));
      addLog("Cycle complete ✓");
      setIsScanning(false);
      return result;
    },
    onSuccess: (data) => {
      refetchStatus();
      setLastCycleResult(data);
    },
  });

  const seedMutation = useMutation({
    mutationFn: () => postJson("/api/seed"),
    onSuccess: () => {
      addLog("Demo signals loaded — 3 sample markets with AI analysis");
    },
  });

  const { signTypedDataAsync } = useSignTypedData();
  const { writeContractAsync } = useWriteContract();

  const { data: usdcBalance } = useReadContract({
    address: USDC_ADDRESS,
    abi: USDC_ABI,
    functionName: "balanceOf",
    args: address ? [address] : undefined,
    query: { enabled: !!address },
  });

  const subscribeMutation = useMutation({
    mutationFn: async (addr: string) => {
      if (!isConnected) {
        throw new Error("Wallet not connected");
      }
      
      addLog("Fetching x402 payment requirements from Circle Gateway...");
      const requirements = await fetchJson(`/api/subscribe/payment-requirements?user_address=${addr}&price=0.01`);

      if (requirements.eip712_domain) {
        addLog("Signing EIP-712 authorization for Circle Nanopayments...");
        const domain = requirements.eip712_domain;
        const types = {
          TransferWithAuthorization: [
            { name: "from", type: "address" },
            { name: "to", type: "address" },
            { name: "value", type: "uint256" },
            { name: "validAfter", type: "uint256" },
            { name: "validBefore", type: "uint256" },
            { name: "nonce", type: "bytes32" },
          ],
        };

        const validBefore = BigInt(Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60);
        const nonce = `0x${Array.from(crypto.getRandomValues(new Uint8Array(32))).map(b => b.toString(16).padStart(2, "0")).join("")}`;

        const message = {
          from: addr as `0x${string}`,
          to: requirements.payTo as `0x${string}`,
          value: BigInt(requirements.amount),
          validAfter: BigInt(0),
          validBefore,
          nonce: nonce as `0x${string}`,
        };

        const signature = await signTypedDataAsync({
          domain: {
            name: domain.name,
            version: domain.version,
            chainId: domain.chainId,
            verifyingContract: domain.verifyingContract as `0x${string}`,
          },
          types,
          primaryType: "TransferWithAuthorization",
          message,
        });

        addLog("Signature obtained, submitting to Circle Gateway for x402 settlement...");
        return postJson("/api/subscribe", {
          user_address: addr,
          price_per_signal: 0.01,
          signed_payload: {
            authorization: {
              from: message.from,
              to: requirements.payTo,
              value: message.value.toString(),
              validAfter: message.validAfter.toString(),
              validBefore: message.validBefore.toString(),
              nonce: message.nonce,
            },
            signature,
          },
        });
      }

      return postJson("/api/subscribe", { user_address: addr });
    },
    onSuccess: async (_, addr) => {
      refetchStatus();
      await refetchSubscriptions();
      setShowSubscriptions(true);
      addLog(`Subscribed: ${addr.slice(0, 8)}... — $0.01/signal via Circle Nanopayments`);
    },
    onError: (error: any) => {
      addLog(`Subscribe failed: ${error?.message || error}`);
    },
  });

  const handleConfigChange = async (key: string, value: string | number | boolean) => {
    await putJson("/api/config", { [key]: value });
    refetchConfig();
    addLog(`Config updated: ${key} = ${value}`);
  };

  const handleSubscribe = () => {
    const addr = address || subAddress || "";
    if (addr) {
      subscribeMutation.mutate(addr);
      setSubAddress("");
    }
  };

  const dismissHelp = () => {
    setShowHelp(false);
    localStorage.setItem("signalforge-help-dismissed", "1");
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <p className="text-[#00ff41] font-mono text-sm animate-pulse">
          initializing signalforge<span className="animate-blink">_</span>
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Help Overlay */}
      {showHelp && (
        <div className="fixed inset-0 z-50 bg-[#0a0a0f]/95 flex items-center justify-center p-4">
          <div className="max-w-xl w-full terminal-panel terminal-panel-active">
            <div className="terminal-header">
              welcome to signalforge
              <span className="flex-1" />
              <button onClick={dismissHelp} className="text-[#6a6a8a] hover:text-[#00ff41] text-xs">✕ close</button>
            </div>
            <div className="p-6 space-y-5">
              <div className="text-center">
                <h2 className="text-lg font-bold text-[#00ff41] mb-1">
                  SIGNAL<span className="text-[#00f0ff]">FORGE</span>
                </h2>
                <p className="text-[11px] text-[#6a6a8a]">Reasoning as a Service — AI agent that sells its thinking</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <span className="text-[#00ff41] font-bold mt-0.5">01</span>
                  <div>
                    <p className="text-xs text-[#e0e0e0] font-semibold">AI analyzes markets</p>
                    <p className="text-[11px] text-[#6a6a8a]">DGrid AI scans 50 Polymarket markets, finds +EV bets</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <span className="text-[#00f0ff] font-bold mt-0.5">02</span>
                  <div>
                    <p className="text-xs text-[#e0e0e0] font-semibold">Reasoning anchored on Arc</p>
                    <p className="text-[11px] text-[#6a6a8a]">Every decision hashed and stored on Arc (~$0.01/tx) — verifiable, permanent</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <span className="text-[#f0e130] font-bold mt-0.5">03</span>
                  <div>
                    <p className="text-xs text-[#e0e0e0] font-semibold">Subscribe & copy-trade</p>
                    <p className="text-[11px] text-[#6a6a8a]">Pay $0.01/signal via Circle Nanopayments. Copy the agent's trades.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <span className="text-[#b829dd] font-bold mt-0.5">04</span>
                  <div>
                    <p className="text-xs text-[#e0e0e0] font-semibold">Cross-chain via Circle Gateway</p>
                    <p className="text-[11px] text-[#6a6a8a]">Unified USDC balance across chains. Move capital where it's needed.</p>
                  </div>
                </div>
              </div>

              <div className="border-t border-[#1a1a2e] pt-4 space-y-2">
                <p className="text-[10px] text-[#6a6a8a] uppercase tracking-wider font-semibold">Quick start</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => { dismissHelp(); seedMutation.mutate(); }}
                    className="cyber-btn cyber-btn-primary text-center justify-center py-3"
                  >
                    ◈ load demo
                  </button>
                  <button
                    onClick={() => { dismissHelp(); cycleMutation.mutate(); }}
                    className="cyber-btn text-center justify-center py-3"
                  >
                    ⚡ scan live
                  </button>
                </div>
                <p className="text-[10px] text-[#3a3a5a] text-center">
                  Demo shows sample signals · Scan runs real DGrid AI analysis
                </p>
              </div>

              <div className="border-t border-[#1a1a2e] pt-3">
                <p className="text-[10px] text-[#3a3a5a] text-center">
                  Built for <span className="text-[#00f0ff]">Agora Agents Hackathon</span> · Canteen × Circle × Arc × DGrid
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
        {/* Terminal Header */}
        <header className="terminal-panel terminal-panel-active mb-4">
          <div className="terminal-header">
            <span className="text-[#00ff41] font-bold">signalforge</span>
            <span className="text-[#6a6a8a]">v3.0.0</span>
            <span className="flex-1" />
            <span className="text-[#6a6a8a]">arc-testnet</span>
            <span className="text-[#6a6a8a]">dgrid-ai</span>
            <span className="text-[#b829dd]">nanopayments</span>
          </div>
          <div className="px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-[#00ff41] font-bold text-lg tracking-tight">
                SIGNAL<span className="text-[#00f0ff]">FORGE</span>
              </span>
              <button
                onClick={() => setShowHelp(true)}
                className="text-[10px] text-[#6a6a8a] hover:text-[#00ff41] transition-colors border border-[#1a1a2e] px-2 py-0.5 rounded"
              >
                ? help
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button className="cyber-btn" onClick={() => setShowTerminal(!showTerminal)}>
                {showTerminal ? "hide" : "show"} terminal
              </button>
              <button className="cyber-btn" onClick={() => setShowStack(!showStack)}>stack</button>
              <button className="cyber-btn" onClick={() => setShowSubscriptions(!showSubscriptions)}>
                subscribers {status?.subscribers || 0}
              </button>
              {isConnected ? (
                <div className="flex items-center gap-2">
                  <span className="text-[9px] text-[#00ff41] font-bold border border-[#00ff41]/30 px-2 py-0.5 rounded">
                    ● circle wallet
                  </span>
                  <button className="cyber-btn" onClick={() => disconnect()}>
                    <span className="text-[#00f0ff]">{address?.slice(0, 6)}...{address?.slice(-4)}</span>
                  </button>
                </div>
              ) : (
                <button className="cyber-btn cyber-btn-primary" onClick={() => connect({ connector: injected() })}>
                  connect circle wallet
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Arc + Circle Status Bar */}
        <div className="terminal-panel mb-4">
          <div className="terminal-header">
            arc blockchain + circle ecosystem
            <span className="flex-1" />
            <div className="flex items-center gap-3">
              <span className={status?.arc_connected ? "text-[#00ff41]" : "text-[#ff2244]"}>
                {status?.arc_connected ? "● arc" : "○ arc"}
              </span>
              <span className={status?.circle_connected ? "text-[#00f0ff]" : "text-[#ff2244]"}>
                {status?.circle_connected ? "● wallet" : "○ wallet"}
              </span>
              <span className={status?.gateway_connected ? "text-[#f0e130]" : "text-[#ff2244]"}>
                {status?.gateway_connected ? "● gateway" : "○ gateway"}
              </span>
            </div>
          </div>
          <div className="px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-[#6a6a8a]">chain:</span>
              <span className="text-[#00f0ff] font-semibold">Arc Testnet</span>
              <span className="text-[#3a3a5a]">(5042002)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#6a6a8a]">signer:</span>
              <span className="text-[#e0e0e0] font-mono">
                {status?.arc_address?.slice(0, 6)}...{status?.arc_address?.slice(-4) || "—"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#6a6a8a]">circle wallet:</span>
              <span className="text-[#b829dd] font-mono">
                {status?.circle_wallet_address?.slice(0, 6)}...{status?.circle_wallet_address?.slice(-4) || "—"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#6a6a8a]">balance:</span>
              <span className="text-[#f0e130] font-bold">${status?.circle_usdc_balance?.toFixed(2) || "0.00"}</span>
              <span className="text-[#6a6a8a]">USDC</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#6a6a8a]">gas:</span>
              <span className="text-[#00ff41]">~$0.01/tx</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#6a6a8a]">traces:</span>
              <span className="text-[#b829dd] font-bold">{status?.total_trades ?? 0}</span>
              <span className="text-[#6a6a8a]">anchored</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#6a6a8a]">revenue:</span>
              <span className="text-[#00ff41] font-bold">${status?.subscription_revenue?.toFixed(4) || "0.0000"}</span>
            </div>
            <a href="https://testnet.arcscan.app" target="_blank" rel="noopener noreferrer" className="cyber-link ml-auto">
              ↗ arcscan
            </a>
          </div>
        </div>

        {/* Agent Activity Terminal */}
        {showTerminal && (
          <div className="terminal-panel mb-4 border border-[#00ff41]/20">
            <div className="terminal-header">
              <span className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${isScanning ? "bg-[#00ff41] animate-pulse" : "bg-[#3a3a5a]"}`} />
                agent activity log
              </span>
              <span className="flex-1" />
              <button onClick={() => setAgentLogs([])} className="text-[10px] text-[#6a6a8a] hover:text-[#00ff41]">clear</button>
            </div>
            <div className="p-3 bg-[#050508] font-mono text-[11px] h-48 overflow-y-auto space-y-0.5">
              {agentLogs.length === 0 ? (
                <p className="text-[#3a3a5a]">waiting for agent activity...</p>
              ) : (
                agentLogs.map((log, i) => (
                  <p key={i} className={`${
                    log.includes("✓") ? "text-[#00ff41]" :
                    log.includes("Error") || log.includes("failed") ? "text-[#ff2244]" :
                    log.includes("USDC") || log.includes("settlement") ? "text-[#f0e130]" :
                    log.includes("Arc") || log.includes("anchoring") ? "text-[#b829dd]" :
                    log.includes("DGrid") || log.includes("AI") ? "text-[#00f0ff]" :
                    "text-[#6a6a8a]"
                  }`}>
                    {log}
                  </p>
                ))
              )}
              {isScanning && (
                <p className="text-[#00ff41] animate-pulse">▊</p>
              )}
            </div>
          </div>
        )}

        {/* Circle Stack Panel */}
        {showStack && stack && (
          <div className="terminal-panel mb-4">
            <div className="terminal-header">circle developer stack</div>
            <div className="p-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
              {Object.entries(stack).map(([key, val]: [string, any]) => (
                <div key={key} className="p-2 rounded border border-[#1a1a2e] bg-[#0d0d14]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-semibold text-[#e0e0e0]">{val.name}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                      val.status === "integrated"
                        ? "bg-[#00ff41]/10 text-[#00ff41] border border-[#00ff41]/20"
                        : "bg-[#1a1a2e] text-[#6a6a8a]"
                    }`}>
                      {val.status}
                    </span>
                  </div>
                  <p className="text-[10px] text-[#6a6a8a] leading-snug">{val.use_case}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Subscription Panel */}
        {showSubscriptions && (
          <div className="terminal-panel mb-4 border border-[#f0e130]/20">
            <div className="terminal-header">
              subscriptions — reasoning as a service
              <span className="flex-1" />
              <span className="text-[#00ff41]">{subStats?.total_subscribers || 0} active</span>
            </div>
            <div className="px-4 py-4">
              {/* Pricing Card */}
              <div className="mb-4 p-4 bg-gradient-to-r from-[#0d0d14] to-[#0a0a0f] border border-[#1a1a2e] rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[#00ff41]">SignalForge Pro</h3>
                    <p className="text-[10px] text-[#6a6a8a]">AI-powered prediction market signals</p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-[#f0e130]">$0.01</div>
                    <div className="text-[9px] text-[#6a6a8a] uppercase">per signal</div>
                  </div>
                </div>
                <div className="mb-3 p-3 bg-[#07070c] rounded border border-[#1a1a2e]">
                  <div className="text-[10px] text-[#6a6a8a] mb-1">how nanopayments work</div>
                  <div className="text-[11px] text-[#e0e0e0] space-y-1">
                    <p>1. Sign EIP-712 authorization (gas-free, off-chain)</p>
                    <p>2. <span className="text-[#00f0ff]">Circle Gateway</span> verifies & batches via x402 protocol</p>
                    <p>3. Batch settled on Arc periodically — batch ID shown below</p>
                    <p>4. $0.01/signal · gas-free · cross-chain via Gateway</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 text-center mb-3">
                  <div className="p-2 bg-[#07070c] rounded border border-[#1a1a2e]">
                    <div className="text-xs font-bold text-[#00f0ff]">DGrid AI</div>
                    <div className="text-[9px] text-[#6a6a8a]">analysis engine</div>
                  </div>
                  <div className="p-2 bg-[#07070c] rounded border border-[#1a1a2e]">
                    <div className="text-xs font-bold text-[#b829dd]">Arc</div>
                    <div className="text-[9px] text-[#6a6a8a]">trace anchoring</div>
                  </div>
                  <div className="p-2 bg-[#07070c] rounded border border-[#1a1a2e]">
                    <div className="text-xs font-bold text-[#00ff41]">Circle</div>
                    <div className="text-[9px] text-[#6a6a8a]">nanopayments</div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <input
                    type="text"
                    placeholder="wallet address or connect"
                    value={subAddress}
                    onChange={(e) => setSubAddress(e.target.value)}
                    className="flex-1 min-w-[200px] bg-[#0d0d14] border border-[#1a1a2e] text-[#e0e0e0] text-xs px-3 py-2 rounded font-mono outline-none focus:border-[#00ff41]"
                  />
                  {isConnected && (
                    <button
                      className="cyber-btn"
                      onClick={() => setShowDepositPrompt(true)}
                      disabled={subscribeMutation.isPending || !(subAddress || address)}
                    >
                      {subscribeMutation.isPending ? "subscribing..." : "⚡ subscribe now"}
                    </button>
                  )}
                </div>

                {/* Deposit Prompt */}
                {showDepositPrompt && (
                  <div className="mt-4 p-4 bg-[#07070c] border border-[#f0e130]/30 rounded-lg">
                    <div className="flex items-start gap-3">
                      <span className="text-[#f0e130] text-lg">◈</span>
                      <div className="flex-1">
                        <h4 className="text-sm font-bold text-[#f0e130] mb-1">Circle Nanopayments (x402)</h4>
                        <p className="text-[11px] text-[#6a6a8a] mb-3">
                          Sign an EIP-712 authorization to pay $0.01/signal via Circle Gateway. Gas-free, batched settlement on Arc.
                        </p>
                        <div className="flex items-center gap-3 mb-3">
                          <div className="flex-1 p-2 bg-[#0d0d14] rounded border border-[#1a1a2e]">
                            <div className="text-[9px] text-[#6a6a8a] uppercase">Your USDC Balance</div>
                            <div className="text-sm font-bold text-[#00ff41]">
                              {usdcBalance ? `$${formatUnits(usdcBalance, 6)}` : "Loading..."}
                            </div>
                          </div>
                          <div className="flex-1 p-2 bg-[#0d0d14] rounded border border-[#1a1a2e]">
                            <div className="text-[9px] text-[#6a6a8a] uppercase">Price</div>
                            <div className="text-sm font-bold text-[#00f0ff]">$0.01/signal</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            className="cyber-btn cyber-btn-primary"
                            onClick={() => {
                              setShowDepositPrompt(false);
                              handleSubscribe();
                            }}
                            disabled={!usdcBalance || usdcBalance === BigInt(0)}
                          >
                            sign & subscribe via x402
                          </button>
                          <button
                            className="cyber-btn"
                            onClick={() => setShowDepositPrompt(false)}
                          >
                            cancel
                          </button>
                        </div>
                        {usdcBalance === BigInt(0) && (
                          <p className="text-[10px] text-[#ff2244] mt-2">
                            No USDC in wallet. Get testnet USDC from <a href="https://faucet.circle.com" target="_blank" rel="noopener noreferrer" className="text-[#00f0ff] underline">faucet.circle.com</a>
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Subscriber List */}
              {subscriptions && subscriptions.length > 0 && (
                <div className="mb-3">
                  <div className="text-[9px] font-bold text-[#6a6a8a] uppercase tracking-widest mb-2">active subscribers</div>
                  <div className="space-y-1">
                    {subscriptions.map((sub: any) => (
                      <div key={sub.id} className="text-xs py-2 px-3 bg-[#07070c] rounded border border-[#1a1a2e]">
                        <div className="flex items-center justify-between">
                          <span className="text-[#e0e0e0] font-mono">{sub.user_address.slice(0, 10)}...{sub.user_address.slice(-6)}</span>
                          <span className="text-[#6a6a8a]">{sub.signals_received} signals</span>
                          <span className="text-[#00ff41]">${sub.total_paid?.toFixed(4)}</span>
                        </div>
                        {sub.payment_txs && sub.payment_txs.length > 0 && (
                          <div className="mt-1.5 space-y-0.5">
                            {sub.payment_txs.slice(-3).map((tx: any, j: number) => (
                              <div key={j} className="flex items-center gap-2 text-[10px]">
                                <span className="text-[#00f0ff]">◈</span>
                                <span className="text-[#6a6a8a] font-mono">{tx.tx_hash?.slice(0, 12)}...</span>
                                <span className="text-[#00ff41]">${tx.amount}</span>
                                <span className="text-[9px] px-1 py-0 rounded bg-[#00f0ff]/10 text-[#00f0ff] border border-[#00f0ff]/20">x402 batch</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Stats */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 bg-[#07070c] rounded border border-[#1a1a2e]">
                  <div className="text-lg font-bold text-[#00ff41]">{subStats?.total_signals_delivered || 0}</div>
                  <div className="text-[9px] text-[#6a6a8a] uppercase">signals delivered</div>
                </div>
                <div className="p-3 bg-[#07070c] rounded border border-[#1a1a2e]">
                  <div className="text-lg font-bold text-[#f0e130]">${subStats?.total_revenue_usd?.toFixed(4) || "0.0000"}</div>
                  <div className="text-[9px] text-[#6a6a8a] uppercase">revenue</div>
                </div>
                <div className="p-3 bg-[#07070c] rounded border border-[#1a1a2e]">
                  <div className="text-lg font-bold text-[#b829dd]">{subStats?.total_copy_trades || 0}</div>
                  <div className="text-[9px] text-[#6a6a8a] uppercase">copy trades</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Portfolio Bar */}
        {portfolio && signals && signals.length > 0 && (
          <div className="terminal-panel terminal-panel-active mb-4">
            <div className="terminal-header">portfolio</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-[#1a1a2e]">
              <div className="p-4 text-center">
                <div className="text-2xl font-bold text-[#00ff41]">${portfolio.total_exposure?.toFixed(0) || 0}</div>
                <div className="text-[10px] text-[#6a6a8a] uppercase tracking-widest mt-1">exposure</div>
              </div>
              <div className="p-4 text-center">
                <div className="text-2xl font-bold text-[#00f0ff]">{signals.length}</div>
                <div className="text-[10px] text-[#6a6a8a] uppercase tracking-widest mt-1">signals</div>
              </div>
              <div className="p-4 text-center">
                <div className="text-2xl font-bold text-[#f0e130]">${portfolio.avg_position_size?.toFixed(0) || 0}</div>
                <div className="text-[10px] text-[#6a6a8a] uppercase tracking-widest mt-1">avg pos</div>
              </div>
              <div className="p-4 text-center">
                <div className="text-2xl font-bold text-[#b829dd] capitalize">{portfolio.risk_level}</div>
                <div className="text-[10px] text-[#6a6a8a] uppercase tracking-widest mt-1">risk</div>
              </div>
            </div>
          </div>
        )}

        {/* Controls */}
        <div className="terminal-panel mb-4">
          <div className="terminal-header">control panel</div>
          <div className="px-4 py-3">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <span className={status?.is_running ? "status-dot-active" : "status-dot-inactive"} />
                <span className="text-xs font-mono text-[#6a6a8a]">
                  {status?.is_running ? "AUTO-RUNNING" : "IDLE"}
                </span>
                {status?.is_running && (
                  <span className="text-[10px] text-[#3a3a5a]">
                    (every {status?.auto_cycle_minutes || 15}min)
                  </span>
                )}
              </div>

              <button
                className={`cyber-btn ${status?.is_running ? "cyber-btn-danger" : "cyber-btn-primary"}`}
                onClick={() => status?.is_running ? stopMutation.mutate() : startMutation.mutate()}
              >
                {status?.is_running ? "■ stop auto" : "▶ auto-run"}
              </button>

              <button
                className="cyber-btn"
                onClick={() => cycleMutation.mutate()}
                disabled={cycleMutation.isPending}
              >
                {cycleMutation.isPending ? "⟳ scanning..." : isScanning ? "⏳ processing..." : "⚡ scan once"}
              </button>

              <button className="cyber-btn" onClick={() => seedMutation.mutate()}>◈ demo</button>

              <div className="flex items-center gap-4 ml-auto">
                {[
                  { label: "cycles", value: status?.total_cycles || 0 },
                  { label: "signals", value: status?.total_signals || 0 },
                  { label: "trades", value: status?.total_trades || 0 },
                  { label: "volume", value: `$${status?.total_volume?.toFixed(0) || 0}` },
                ].map((s) => (
                  <div key={s.label} className="text-center">
                    <div className="text-sm font-bold text-[#e0e0e0]">{s.value}</div>
                    <div className="text-[9px] text-[#6a6a8a] uppercase tracking-wider">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {lastCycleResult && (
              <div className="mt-2 px-3 py-2 bg-[#07070c] border border-[#1a1a2e] rounded text-[11px] text-[#6a6a8a]">
                <span className="text-[#00ff41]">✓</span> cycle #{lastCycleResult.cycle} — {lastCycleResult.signals_found} signals found
              </div>
            )}

            <div className="flex flex-wrap gap-x-4 gap-y-2 mt-3 pt-3 border-t border-[#1a1a2e]">
              <ConfigSelect label="strategy" value={config?.mode || "balanced"} options={[
                { value: "value", label: "Value" }, { value: "momentum", label: "Momentum" },
                { value: "catalyst", label: "Catalyst" }, { value: "balanced", label: "Balanced" },
              ]} onChange={(v) => handleConfigChange("mode", v)} />
              <ConfigSelect label="risk" value={config?.risk || "moderate"} options={[
                { value: "conservative", label: "Conservative" }, { value: "moderate", label: "Moderate" },
                { value: "aggressive", label: "Aggressive" },
              ]} onChange={(v) => handleConfigChange("risk", v)} />
              <ConfigSelect label="max_bet" value={config?.max_position_usd || 25} options={[
                { value: 10, label: "$10" }, { value: 25, label: "$25" },
                { value: 50, label: "$50" }, { value: 100, label: "$100" },
              ]} onChange={(v) => handleConfigChange("max_position_usd", Number(v))} />
              <ConfigSelect label="min_ev" value={config?.min_ev_pct || 2} options={[
                { value: 1, label: "1%" }, { value: 2, label: "2%" }, { value: 5, label: "5%" },
              ]} onChange={(v) => handleConfigChange("min_ev_pct", Number(v))} />
              <ConfigSelect label="kelly" value={config?.kelly_fraction || 0.25} options={[
                { value: 0.1, label: "0.1x" }, { value: 0.25, label: "0.25x" }, { value: 0.5, label: "0.5x" },
              ]} onChange={(v) => handleConfigChange("kelly_fraction", Number(v))} />
              <ConfigSelect label="mode" value={config?.paper_trade ? "paper" : "live"} options={[
                { value: "paper", label: "Paper Trade" }, { value: "live", label: "Live" },
              ]} onChange={(v) => handleConfigChange("paper_trade", v === "paper")} />
            </div>
          </div>
        </div>

        {/* Signals */}
        <div className="terminal-panel">
          <div className="terminal-header">
            signals & trades
            <span className="flex-1" />
            <span className="text-[#00ff41]">{signals?.length || 0} active</span>
          </div>

          {signals?.length === 0 ? (
            <div className="px-4 py-12 text-center">
              <p className="text-[#6a6a8a] text-sm mb-3">
                <span className="text-[#00ff41]">$</span> no signals loaded
              </p>
              <div className="flex items-center justify-center gap-3">
                <button onClick={() => cycleMutation.mutate()} disabled={cycleMutation.isPending} className="cyber-btn">
                  {cycleMutation.isPending ? "⟳ scanning..." : "⚡ scan live markets"}
                </button>
                <button onClick={() => seedMutation.mutate()} className="cyber-btn">◈ load demo</button>
              </div>
              <p className="text-[10px] text-[#3a3a5a] mt-3">
                Scan fetches 50 Polymarket markets → DGrid AI analyzes → finds +EV bets → anchors reasoning on Arc
              </p>
            </div>
          ) : (
            <div>
              {signals?.map((s: any, i: number) => (
                <div key={i} className="border-b border-[#1a1a2e] last:border-b-0">
                  <div className="signal-row" onClick={() => setExpandedSignal(expandedSignal === i ? null : i)}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] text-[#e0e0e0] truncate font-medium">
                          <span className="text-[#00ff41] mr-1">{String(i + 1).padStart(2, "0")}.</span>
                          {s.market.question}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className={`cyber-badge ${s.action.includes("BUY") ? "cyber-badge-green" : "cyber-badge-red"}`}>
                            {s.action}
                          </span>
                          {s.market.category && (
                            <span className="cyber-badge cyber-badge-cyan">{s.market.category}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-5 shrink-0">
                        <div className="text-right">
                          <div className="text-sm font-bold text-[#f0e130]">${s.position_size_usd}</div>
                          <div className="text-[9px] text-[#6a6a8a] uppercase">position</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-bold text-[#00ff41]">{s.edge_pct}%</div>
                          <div className="text-[9px] text-[#6a6a8a] uppercase">edge</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-bold text-[#00f0ff]">{s.confidence}%</div>
                          <div className="text-[9px] text-[#6a6a8a] uppercase">conf</div>
                        </div>
                        <div className="text-right w-32">
                          <div className="text-[10px] text-[#6a6a8a]">
                            AI <span className="text-[#00ff41] font-bold">{(s.estimated_probability * 100).toFixed(0)}%</span>
                          </div>
                          <div className="text-[10px] text-[#6a6a8a]">
                            MKT <span className="text-[#e0e0e0] font-bold">{(s.market_implied_probability * 100).toFixed(0)}%</span>
                          </div>
                          {(() => {
                            const isReal = s.reasoning?.arc_tx_hash?.startsWith("0x") && s.reasoning?.arc_tx_hash?.length === 66;
                            return isReal ? (
                              <a
                                href={`https://testnet.arcscan.app/tx/${s.reasoning.arc_tx_hash}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[9px] text-[#b829dd] hover:text-[#b829dd]/80 underline underline-offset-2 block mt-0.5"
                              >
                                ↗ trace
                              </a>
                            ) : s.reasoning?.arc_tx_hash ? (
                              <span className="text-[9px] text-[#f0e130] block mt-0.5">◈ demo</span>
                            ) : (
                              <span className="text-[9px] text-[#3a3a5a] block mt-0.5">not anchored</span>
                            );
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>

                  {expandedSignal === i && (
                    <div className="px-4 py-3 bg-[#07070c] border-t border-[#1a1a2e]">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                          <div className="text-[9px] font-bold text-[#6a6a8a] uppercase tracking-widest mb-2 flex items-center gap-1">
                            <span className="text-[#00ff41]">▸</span> analysis
                          </div>
                          <p className="text-[11px] text-[#a1a1aa] leading-relaxed">{s.reasoning?.analysis}</p>
                        </div>
                        <div>
                          <div className="text-[9px] font-bold text-[#6a6a8a] uppercase tracking-widest mb-2 flex items-center gap-1">
                            <span className="text-[#00ff41]">▸</span> factors
                          </div>
                          <ul className="space-y-1">
                            {s.reasoning?.key_factors?.map((f: string, j: number) => (
                              <li key={j} className="text-[10px] text-[#00ff41] flex items-start gap-1.5">
                                <span className="text-[#00ff41] mt-0.5">+</span><span>{f}</span>
                              </li>
                            ))}
                          </ul>
                          <div className="text-[9px] font-bold text-[#6a6a8a] uppercase tracking-widest mb-2 mt-3 flex items-center gap-1">
                            <span className="text-[#ff2244]">▸</span> risks
                          </div>
                          <ul className="space-y-1">
                            {s.reasoning?.risks?.map((r: string, j: number) => (
                              <li key={j} className="text-[10px] text-[#ff2244] flex items-start gap-1.5">
                                <span className="mt-0.5">−</span><span>{r}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <div className="text-[9px] font-bold text-[#6a6a8a] uppercase tracking-widest mb-2 flex items-center gap-1">
                            <span className="text-[#00ff41]">▸</span> metadata
                          </div>
                          <div className="space-y-1.5 text-[10px] text-[#6a6a8a]">
                            <p>model: <span className="text-[#e0e0e0]">{s.reasoning?.model_used || "dgrid"}</span></p>
                            <p>kelly: <span className="text-[#e0e0e0]">{s.kelly_fraction}x</span></p>
                            <p>version: <span className="text-[#e0e0e0]">{s.version}</span></p>
                            {(() => {
                              const isReal = s.reasoning?.arc_tx_hash?.startsWith("0x") && s.reasoning?.arc_tx_hash?.length === 66;
                              return isReal ? (
                                <a href={`https://testnet.arcscan.app/tx/${s.reasoning.arc_tx_hash}`} target="_blank" rel="noopener noreferrer" className="cyber-link block mt-2">
                                  ↗ arcscan tx
                                </a>
                              ) : s.reasoning?.arc_tx_hash ? (
                                <span className="text-[#f0e130] block mt-2">◈ demo trace</span>
                              ) : null;
                            })()}
                            <a href={s.market.url} target="_blank" rel="noopener noreferrer" className="cyber-link block">
                              ↗ polymarket
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Trade History */}
        {trades && trades.length > 0 && (
          <div className="terminal-panel mt-4">
            <div className="terminal-header">
              trade history
              <span className="flex-1" />
              <span className="text-[#6a6a8a]">{trades.length} records</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full cyber-table">
                <thead>
                  <tr>
                    <th className="text-left">market</th>
                    <th className="text-left">action</th>
                    <th className="text-right">size</th>
                    <th className="text-right">price</th>
                    <th className="text-right">mode</th>
                    <th className="text-right">arc trace</th>
                    <th className="text-right">settlement</th>
                    <th className="text-right">status</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t: any, i: number) => (
                    <tr key={i}>
                      <td className="text-[#e0e0e0] truncate max-w-[200px]">{t.signal?.market?.question}</td>
                      <td>
                        <span className={`cyber-badge ${t.action.includes("BUY") ? "cyber-badge-green" : "cyber-badge-red"}`}>
                          {t.action}
                        </span>
                      </td>
                      <td className="text-right text-[#f0e130]">${t.size_usd}</td>
                      <td className="text-right text-[#6a6a8a]">${t.filled_price}</td>
                      <td className="text-right">
                        <span className={`cyber-badge ${t.mode === "simulated" ? "cyber-badge-purple" : "cyber-badge-green"}`}>
                          {t.mode === "simulated" ? "paper" : "live"}
                        </span>
                      </td>
                      <td className="text-right">
                        {(() => {
                          const isReal = t.arc_trace_hash?.startsWith("0x") && t.arc_trace_hash?.length === 66;
                          return isReal ? (
                            <a href={`https://testnet.arcscan.app/tx/${t.arc_trace_hash}`} target="_blank" rel="noopener noreferrer" className="cyber-link text-[10px]">
                              ↗ trace
                            </a>
                          ) : t.arc_trace_hash ? (
                            <span className="text-[#6a6a8a] text-[10px] font-mono">{t.arc_trace_hash.slice(0, 10)}...</span>
                          ) : (
                            <span className="text-[#3a3a5a] text-[10px]">—</span>
                          );
                        })()}
                      </td>
                      <td className="text-right">
                        {(() => {
                          const isReal = t.gateway_tx?.startsWith("0x") && t.gateway_tx?.length === 66;
                          return isReal ? (
                            <a href={`https://testnet.arcscan.app/tx/${t.gateway_tx}`} target="_blank" rel="noopener noreferrer" className="cyber-link text-[10px] text-[#f0e130]">
                              ↗ $0.10 usdc
                            </a>
                          ) : t.gateway_tx ? (
                            <span className="text-[#6a6a8a] text-[10px] font-mono">{t.gateway_tx.slice(0, 10)}...</span>
                          ) : (
                            <span className="text-[#3a3a5a] text-[10px]">—</span>
                          );
                        })()}
                      </td>
                      <td className="text-right text-[#6a6a8a]">{t.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-4 pt-3 border-t border-[#1a1a2e] text-center animate-flicker">
          <p className="text-[10px] text-[#3a3a5a] font-mono">
            <span className="text-[#00ff41]">$</span> signalforge · agora agents · canteen × circle × arc × dgrid
          </p>
          <p className="text-[10px] text-[#3a3a5a] mt-0.5">
            reasoning as a service · settled on arc · paid in usdc nanopayments
          </p>
          <p className="text-[9px] text-[#6a6a8a] mt-1">
            mainnet: circle gateway + cctp for cross-chain usdc settlement
          </p>
          <p className="text-[9px] text-[#3a3a5a] mt-2">
            built with obsession for the <span className="text-[#00f0ff]">agora</span> — where agents think out loud
          </p>
        </footer>
      </div>
    </div>
  );
}

function ConfigSelect({ label, value, options, onChange }: { label: string; value: string | number; options: { value: string | number; label: string }[]; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] text-[#6a6a8a] font-mono uppercase">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="cyber-select">
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}
