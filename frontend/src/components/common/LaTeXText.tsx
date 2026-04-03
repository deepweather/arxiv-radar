import { latexToHtml } from "@/utils/latex";

interface LaTeXTextProps {
  text: string;
  className?: string;
  as?: keyof JSX.IntrinsicElements;
}

export default function LaTeXText({ text, className, as: Tag = "span" }: LaTeXTextProps) {
  const html = latexToHtml(text);
  return <Tag className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}
