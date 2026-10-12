import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";
import bash from "highlight.js/lib/languages/bash";
import markdown from "highlight.js/lib/languages/markdown";
import "highlight.js/styles/github-dark.css";

hljs.registerLanguage("python", python);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("jsx", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("tsx", typescript);
hljs.registerLanguage("json", json);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("html", xml);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("text", markdown);

const ALIASES: Record<string, string> = {
  py: "python",
  js: "javascript",
  ts: "typescript",
  md: "markdown",
  sh: "bash",
};

export function highlight(source: string, language: string): string {
  const name = ALIASES[language] ?? language;
  if (hljs.getLanguage(name)) {
    return hljs.highlight(source, { language: name }).value;
  }
  return hljs.highlightAuto(source).value;
}