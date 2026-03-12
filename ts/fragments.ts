/**
 * data-utils/ts/fragments.ts
 *
 * TypeScript fragment parser — mirrors data_utils/parser.py.
 * Intended to be copied or symlinked into consuming frontends.
 */

// --- Types ---

export type FragmentType =
  | 'frontmatter'
  | 'heading'
  | 'paragraph'
  | 'code_block'
  | 'mermaid'
  | 'yaml_block'
  | 'list'
  | 'hr'
  | 'footnote';

export interface Fragment {
  id: string;
  type: FragmentType;
  content: string;
  line_start: number;
  line_end: number;
  level: number;      // heading level 1-6, 0 otherwise
  lang: string;       // code block language
  meta: Record<string, unknown>;
}

// --- ID generation ---

async function sha256Hex(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
}

/** Synchronous hash for environments without SubtleCrypto — simple djb2-based. */
function hashSync(text: string): string {
  let h = 5381;
  for (let i = 0; i < text.length; i++) {
    h = ((h << 5) + h + text.charCodeAt(i)) >>> 0;
  }
  return h.toString(16).padStart(8, '0').slice(0, 8);
}

function fragmentId(lineStart: number, content: string): string {
  return `${lineStart}:${hashSync(content)}`;
}

// --- Footnote regex ---

const FOOTNOTE_RE = /^\[\^([^\]]+)\]:\s*(.+?)(?:\s*--\s*by:(\S+))?\s*$/;

// --- Mermaid helpers ---

const DIAGRAM_KEYWORDS = /^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|gitgraph|mindmap|timeline|sankey|xychart|block|journey|quadrant)(\s|$)/gm;

function stripFrontmatter(text: string): { body: string; fm: string | null } {
  if (text.startsWith('---')) {
    const end = text.indexOf('\n---', 3);
    if (end !== -1) {
      return { body: text.slice(end + 4), fm: text.slice(3, end).trim() };
    }
  }
  return { body: text, fm: null };
}

function splitDiagrams(text: string): string[] {
  const starts: number[] = [];
  let m: RegExpExecArray | null;
  DIAGRAM_KEYWORDS.lastIndex = 0;
  while ((m = DIAGRAM_KEYWORDS.exec(text)) !== null) {
    starts.push(m.index);
  }
  if (starts.length === 0) return text.trim() ? [text] : [];
  return starts.map((s, i) => {
    const end = i + 1 < starts.length ? starts[i + 1] : text.length;
    return text.slice(s, end).trim();
  }).filter(Boolean);
}

// --- Parsers ---

function parseYaml(text: string): Fragment[] {
  if (!text.trim()) return [];
  return [{
    id: fragmentId(1, text),
    type: 'yaml_block',
    content: text,
    line_start: 1,
    line_end: text.split('\n').length,
    level: 0,
    lang: '',
    meta: {},
  }];
}

function parseMermaid(text: string): Fragment[] {
  const fragments: Fragment[] = [];
  const { body, fm } = stripFrontmatter(text);

  if (fm !== null) {
    const fmLines = text.slice(0, text.indexOf('\n---', 3) + 4).split('\n').length;
    fragments.push({
      id: fragmentId(1, fm),
      type: 'frontmatter',
      content: fm,
      line_start: 1,
      line_end: fmLines,
      level: 0,
      lang: '',
      meta: {},
    });
  }

  const diagrams = splitDiagrams(body);
  let offset = fragments.length > 0 ? fragments[fragments.length - 1].line_end + 1 : 1;
  for (const diagram of diagrams) {
    const lineCount = diagram.split('\n').length;
    fragments.push({
      id: fragmentId(offset, diagram),
      type: 'mermaid',
      content: diagram,
      line_start: offset,
      line_end: offset + lineCount - 1,
      level: 0,
      lang: '',
      meta: {},
    });
    offset += lineCount;
  }
  return fragments;
}

function parseMarkdown(text: string): Fragment[] {
  const fragments: Fragment[] = [];
  const lines = text.split('\n');
  let i = 0;
  const n = lines.length;

  // Frontmatter
  if (lines[0]?.trim() === '---') {
    let endIdx: number | null = null;
    for (let j = 1; j < n; j++) {
      if (lines[j].trim() === '---') { endIdx = j; break; }
    }
    if (endIdx !== null) {
      const fmContent = lines.slice(1, endIdx).join('\n');
      // Parse YAML frontmatter keys into meta (simple key: value)
      const meta: Record<string, unknown> = {};
      for (const line of lines.slice(1, endIdx)) {
        const kv = line.match(/^(\w[\w_-]*):\s*(.*)/);
        if (kv) {
          let val: unknown = kv[2];
          // Simple type coercion
          if (val === 'true') val = true;
          else if (val === 'false') val = false;
          else if (/^\d+$/.test(kv[2])) val = parseInt(kv[2], 10);
          else if (kv[2].startsWith('[') && kv[2].endsWith(']')) {
            val = kv[2].slice(1, -1).split(',').map(s => s.trim());
          }
          meta[kv[1]] = val;
        }
      }
      fragments.push({
        id: fragmentId(1, fmContent),
        type: 'frontmatter',
        content: fmContent,
        line_start: 1,
        line_end: endIdx + 1,
        level: 0,
        lang: '',
        meta,
      });
      i = endIdx + 1;
    }
  }

  while (i < n) {
    const line = lines[i];
    const lineNum = i + 1;

    // Blank line
    if (line.trim() === '') { i++; continue; }

    // Footnote
    const fnMatch = line.match(FOOTNOTE_RE);
    if (fnMatch) {
      const meta: Record<string, unknown> = { ref: fnMatch[1] };
      if (fnMatch[3]) meta.by = fnMatch[3];
      fragments.push({
        id: fragmentId(lineNum, line),
        type: 'footnote',
        content: fnMatch[2],
        line_start: lineNum,
        line_end: lineNum,
        level: 0,
        lang: '',
        meta,
      });
      i++;
      continue;
    }

    // Horizontal rule
    if (/^---+\s*$/.test(line) || /^\*\*\*+\s*$/.test(line)) {
      fragments.push({
        id: fragmentId(lineNum, line),
        type: 'hr',
        content: line,
        line_start: lineNum,
        line_end: lineNum,
        level: 0,
        lang: '',
        meta: {},
      });
      i++;
      continue;
    }

    // Heading
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/);
    if (headingMatch) {
      fragments.push({
        id: fragmentId(lineNum, line),
        type: 'heading',
        content: headingMatch[2],
        line_start: lineNum,
        line_end: lineNum,
        level: headingMatch[1].length,
        lang: '',
        meta: {},
      });
      i++;
      continue;
    }

    // Code block
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < n && !lines[i].startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      const endLine = i + 1;
      i++; // skip closing ```
      const content = codeLines.join('\n');
      fragments.push({
        id: fragmentId(lineNum, content),
        type: lang === 'mermaid' ? 'mermaid' : 'code_block',
        content,
        line_start: lineNum,
        line_end: endLine,
        level: 0,
        lang,
        meta: {},
      });
      continue;
    }

    // List block
    if (/^\s*[-*+]\s/.test(line) || /^\s*\d+\.\s/.test(line)) {
      const listLines = [line];
      i++;
      while (i < n && (
        /^\s*[-*+]\s/.test(lines[i]) ||
        /^\s*\d+\.\s/.test(lines[i]) ||
        (lines[i].startsWith('  ') && listLines.length > 0)
      )) {
        listLines.push(lines[i]);
        i++;
      }
      const content = listLines.join('\n');
      fragments.push({
        id: fragmentId(lineNum, content),
        type: 'list',
        content,
        line_start: lineNum,
        line_end: lineNum + listLines.length - 1,
        level: 0,
        lang: '',
        meta: {},
      });
      continue;
    }

    // Paragraph
    const paraLines = [line];
    i++;
    while (
      i < n &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('#') &&
      !lines[i].startsWith('```') &&
      !/^---+\s*$/.test(lines[i]) &&
      !/^\s*[-*+]\s/.test(lines[i]) &&
      !/^\s*\d+\.\s/.test(lines[i]) &&
      !FOOTNOTE_RE.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    const content = paraLines.join('\n');
    fragments.push({
      id: fragmentId(lineNum, content),
      type: 'paragraph',
      content,
      line_start: lineNum,
      line_end: lineNum + paraLines.length - 1,
      level: 0,
      lang: '',
      meta: {},
    });
  }

  return fragments;
}

// --- Public API ---

export type FileType = 'md' | 'yaml' | 'yml' | 'mermaid' | 'mmd';

export function parseFragments(text: string, fileType: FileType = 'md'): Fragment[] {
  if (fileType === 'yaml' || fileType === 'yml') return parseYaml(text);
  if (fileType === 'mermaid' || fileType === 'mmd') return parseMermaid(text);
  return parseMarkdown(text);
}

export function detectFileType(filePath: string): FileType {
  const lower = filePath.toLowerCase();
  if (lower.endsWith('.yml') || lower.endsWith('.yaml')) return 'yaml';
  if (lower.endsWith('.mermaid') || lower.endsWith('.mmd')) return 'mermaid';
  return 'md';
}
