import { useState } from "react";
import { Helmet } from "react-helmet-async";
import { Copy, Check, Terminal, FileJson, Zap } from "lucide-react";

type ClientTab = "cursor" | "claude-desktop" | "claude-code";

const MCP_URL = "https://arxivradar.com/mcp/sse";

const CLIENT_CONFIGS: Record<ClientTab, { label: string; language: string; content: string; file?: string }> = {
  cursor: {
    label: "Cursor",
    language: "json",
    file: ".cursor/mcp.json",
    content: `{
  "mcpServers": {
    "arxiv-radar": {
      "type": "sse",
      "url": "${MCP_URL}"
    }
  }
}`,
  },
  "claude-desktop": {
    label: "Claude Desktop",
    language: "json",
    file: "claude_desktop_config.json",
    content: `{
  "mcpServers": {
    "arxiv-radar": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "${MCP_URL}"]
    }
  }
}`,
  },
  "claude-code": {
    label: "Claude Code",
    language: "bash",
    content: `claude mcp add --transport sse arxiv-radar ${MCP_URL}`,
  },
};

const TOOLS = [
  {
    name: "search_papers",
    description: "Semantic search over paper abstracts. Returns papers ranked by relevance.",
    params: "query, limit?, categories?, days?, sort?",
  },
  {
    name: "get_paper",
    description: "Get metadata and abstract for a single paper by arXiv ID.",
    params: "paper_id",
  },
  {
    name: "list_recent_papers",
    description: "Browse recently published papers with optional filters.",
    params: "limit?, categories?, days?, sort?",
  },
  {
    name: "get_similar_papers",
    description: "Find papers similar to a given paper via embedding similarity.",
    params: "paper_id, limit?",
  },
];

function CopyButton({ text, className = "" }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors ${
        copied
          ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950"
          : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
      } ${className}`}
      aria-label="Copy to clipboard"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function CodeBlock({ code, file }: { code: string; file?: string }) {
  return (
    <div className="relative rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-950 overflow-hidden">
      {file && (
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-900">
          <span className="text-xs font-mono text-gray-500 dark:text-gray-400">{file}</span>
          <CopyButton text={code} />
        </div>
      )}
      <pre className="p-4 overflow-x-auto text-sm font-mono text-gray-800 dark:text-gray-200 leading-relaxed">
        {code}
      </pre>
      {!file && (
        <div className="absolute top-2 right-2">
          <CopyButton text={code} />
        </div>
      )}
    </div>
  );
}

export default function ConnectPage() {
  const [clientTab, setClientTab] = useState<ClientTab>("cursor");
  const config = CLIENT_CONFIGS[clientTab];

  return (
    <div className="space-y-10 max-w-2xl">
      <Helmet>
        <title>Connect - arxiv radar</title>
      </Helmet>

      {/* Hero */}
      <div>
        <h1 className="text-2xl font-bold mb-1">Connect your AI agent</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Use the{" "}
          <a
            href="https://modelcontextprotocol.io"
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-600 dark:text-brand-400 hover:underline"
          >
            Model Context Protocol
          </a>{" "}
          to let AI assistants search and retrieve arXiv papers from this instance.
        </p>
      </div>

      {/* Endpoint */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-brand-600 dark:text-brand-400" />
          <h2 className="text-lg font-semibold">Endpoint</h2>
        </div>
        <div className="flex items-center gap-3 p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <code className="flex-1 text-sm font-mono text-gray-800 dark:text-gray-200 break-all">
            {MCP_URL}
          </code>
          <CopyButton text={MCP_URL} />
        </div>
        <p className="text-xs text-gray-400 dark:text-gray-500">
          SSE transport — no authentication required.
        </p>
      </section>

      {/* Setup */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <FileJson size={16} className="text-brand-600 dark:text-brand-400" />
          <h2 className="text-lg font-semibold">Setup</h2>
        </div>

        <div className="flex gap-2">
          {(Object.keys(CLIENT_CONFIGS) as ClientTab[]).map((key) => (
            <button
              key={key}
              onClick={() => setClientTab(key)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                clientTab === key
                  ? "bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                  : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              {CLIENT_CONFIGS[key].label}
            </button>
          ))}
        </div>

        <CodeBlock code={config.content} file={config.file} />

        {clientTab === "cursor" && (
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Add to <code className="font-mono">.cursor/mcp.json</code> in your project root or <code className="font-mono">~/.cursor/mcp.json</code> for global access. Restart Cursor after saving.
          </p>
        )}
        {clientTab === "claude-desktop" && (
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Add to your config file: <code className="font-mono">~/Library/Application Support/Claude/claude_desktop_config.json</code> on macOS.
            Restart Claude Desktop after saving.
          </p>
        )}
        {clientTab === "claude-code" && (
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Add <code className="font-mono">--scope user</code> for global access, or <code className="font-mono">--scope project</code> to share with your team.
          </p>
        )}
      </section>

      {/* Tools reference */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Terminal size={16} className="text-brand-600 dark:text-brand-400" />
          <h2 className="text-lg font-semibold">Available tools</h2>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Every result includes PDF, HTML, and abstract page URLs so agents can fetch full paper content on demand.
        </p>
        <div className="space-y-3">
          {TOOLS.map((tool) => (
            <div
              key={tool.name}
              className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900"
            >
              <div className="flex items-baseline gap-2 mb-1">
                <code className="text-sm font-semibold font-mono text-brand-700 dark:text-brand-400">
                  {tool.name}
                </code>
                <span className="text-xs font-mono text-gray-400 dark:text-gray-500">
                  ({tool.params})
                </span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {tool.description}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
