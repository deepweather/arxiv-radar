import katex from "katex";

function renderMath(tex: string): string {
  try {
    return katex.renderToString(tex, { throwOnError: false, output: "html" });
  } catch {
    return tex;
  }
}

/**
 * Convert LaTeX markup to HTML for display.
 * Uses KaTeX for math expressions, regex for text formatting.
 */
export function latexToHtml(text: string): string {
  if (!text) return "";

  let result = text;

  // Render inline math $...$ via KaTeX (before other replacements)
  result = result.replace(/\$([^$]+)\$/g, (_, math) => renderMath(math));

  // \emph{...} and \textit{...}
  result = result.replace(/\\emph\{([^}]+)\}/g, "<em>$1</em>");
  result = result.replace(/\\textit\{([^}]+)\}/g, "<em>$1</em>");
  result = result.replace(/\\it\{([^}]+)\}/g, "<em>$1</em>");

  // \textbf{...} and \bf{...}
  result = result.replace(/\\textbf\{([^}]+)\}/g, "<strong>$1</strong>");
  result = result.replace(/\\bf\{([^}]+)\}/g, "<strong>$1</strong>");

  // \texttt{...} and \tt{...}
  result = result.replace(/\\texttt\{([^}]+)\}/g, "<code>$1</code>");
  result = result.replace(/\\tt\{([^}]+)\}/g, "<code>$1</code>");

  // \underline{...}
  result = result.replace(/\\underline\{([^}]+)\}/g, "<u>$1</u>");

  // \textsuperscript / \textsubscript
  result = result.replace(/\\textsuperscript\{([^}]+)\}/g, "<sup>$1</sup>");
  result = result.replace(/\\textsubscript\{([^}]+)\}/g, "<sub>$1</sub>");

  // Escaped special characters
  result = result.replace(/\\&/g, "&amp;");
  result = result.replace(/\\%/g, "%");
  result = result.replace(/\\\$/g, "$");
  result = result.replace(/\\#/g, "#");
  result = result.replace(/\\_/g, "_");
  result = result.replace(/\\{/g, "{");
  result = result.replace(/\\}/g, "}");

  // Typographic replacements
  result = result.replace(/\\~/g, "&nbsp;");
  result = result.replace(/~(?!\\)/g, "&nbsp;");
  result = result.replace(/---/g, "\u2014");
  result = result.replace(/--/g, "\u2013");
  result = result.replace(/``/g, "\u201C");
  result = result.replace(/''/g, "\u201D");

  // Clean up remaining \command{content} → content
  result = result.replace(/\\([a-zA-Z]+)\{([^}]*)\}/g, "$2");

  return result;
}
