/**
 * Convert basic LaTeX markup to HTML for display.
 * Handles common commands found in arXiv titles/abstracts.
 */
export function latexToHtml(text: string): string {
  if (!text) return "";

  let result = text;

  // \emph{...} and \textit{...} → <em>...</em>
  result = result.replace(/\\emph\{([^}]+)\}/g, "<em>$1</em>");
  result = result.replace(/\\textit\{([^}]+)\}/g, "<em>$1</em>");
  result = result.replace(/\\it\{([^}]+)\}/g, "<em>$1</em>");

  // \textbf{...} and \bf{...} → <strong>...</strong>
  result = result.replace(/\\textbf\{([^}]+)\}/g, "<strong>$1</strong>");
  result = result.replace(/\\bf\{([^}]+)\}/g, "<strong>$1</strong>");

  // \texttt{...} and \tt{...} → <code>...</code>
  result = result.replace(/\\texttt\{([^}]+)\}/g, "<code>$1</code>");
  result = result.replace(/\\tt\{([^}]+)\}/g, "<code>$1</code>");

  // \underline{...} → <u>...</u>
  result = result.replace(/\\underline\{([^}]+)\}/g, "<u>$1</u>");

  // \textsuperscript{...} → <sup>...</sup>
  result = result.replace(/\\textsuperscript\{([^}]+)\}/g, "<sup>$1</sup>");

  // \textsubscript{...} → <sub>...</sub>
  result = result.replace(/\\textsubscript\{([^}]+)\}/g, "<sub>$1</sub>");

  // Common symbols
  result = result.replace(/\\&/g, "&amp;");
  result = result.replace(/\\%/g, "%");
  result = result.replace(/\\\$/g, "$");
  result = result.replace(/\\#/g, "#");
  result = result.replace(/\\_/g, "_");
  result = result.replace(/\\{/g, "{");
  result = result.replace(/\\}/g, "}");
  result = result.replace(/\\~/g, "&nbsp;");
  result = result.replace(/~(?!\\)/g, "&nbsp;");
  result = result.replace(/---/g, "—");
  result = result.replace(/--/g, "–");
  result = result.replace(/``/g, """);
  result = result.replace(/''/g, """);
  result = result.replace(/`/g, "'");
  result = result.replace(/'/g, "'");

  // Greek letters (common ones)
  const greekLetters: Record<string, string> = {
    "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ",
    "\\epsilon": "ε", "\\zeta": "ζ", "\\eta": "η", "\\theta": "θ",
    "\\iota": "ι", "\\kappa": "κ", "\\lambda": "λ", "\\mu": "μ",
    "\\nu": "ν", "\\xi": "ξ", "\\pi": "π", "\\rho": "ρ",
    "\\sigma": "σ", "\\tau": "τ", "\\upsilon": "υ", "\\phi": "φ",
    "\\chi": "χ", "\\psi": "ψ", "\\omega": "ω",
    "\\Gamma": "Γ", "\\Delta": "Δ", "\\Theta": "Θ", "\\Lambda": "Λ",
    "\\Xi": "Ξ", "\\Pi": "Π", "\\Sigma": "Σ", "\\Phi": "Φ",
    "\\Psi": "Ψ", "\\Omega": "Ω",
  };
  for (const [latex, unicode] of Object.entries(greekLetters)) {
    result = result.replace(new RegExp(latex.replace(/\\/g, "\\\\") + "(?![a-zA-Z])", "g"), unicode);
  }

  // Math symbols
  result = result.replace(/\\times(?![a-zA-Z])/g, "×");
  result = result.replace(/\\cdot(?![a-zA-Z])/g, "·");
  result = result.replace(/\\leq(?![a-zA-Z])/g, "≤");
  result = result.replace(/\\geq(?![a-zA-Z])/g, "≥");
  result = result.replace(/\\neq(?![a-zA-Z])/g, "≠");
  result = result.replace(/\\approx(?![a-zA-Z])/g, "≈");
  result = result.replace(/\\infty(?![a-zA-Z])/g, "∞");
  result = result.replace(/\\pm(?![a-zA-Z])/g, "±");
  result = result.replace(/\\rightarrow(?![a-zA-Z])/g, "→");
  result = result.replace(/\\leftarrow(?![a-zA-Z])/g, "←");
  result = result.replace(/\\Rightarrow(?![a-zA-Z])/g, "⇒");
  result = result.replace(/\\Leftarrow(?![a-zA-Z])/g, "⇐");
  result = result.replace(/\\in(?![a-zA-Z])/g, "∈");
  result = result.replace(/\\subset(?![a-zA-Z])/g, "⊂");
  result = result.replace(/\\sum(?![a-zA-Z])/g, "∑");
  result = result.replace(/\\prod(?![a-zA-Z])/g, "∏");
  result = result.replace(/\\partial(?![a-zA-Z])/g, "∂");
  result = result.replace(/\\nabla(?![a-zA-Z])/g, "∇");

  // Simple inline math $...$ - just remove the delimiters for now
  // (for proper math rendering, would need KaTeX/MathJax)
  result = result.replace(/\$([^$]+)\$/g, "$1");

  // Clean up remaining backslashes before common words (often artifacts)
  result = result.replace(/\\([a-zA-Z]+)\{([^}]*)\}/g, "$2");

  return result;
}
