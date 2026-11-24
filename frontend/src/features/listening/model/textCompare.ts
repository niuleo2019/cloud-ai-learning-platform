/**
 * Word-level comparison between the original sentence and what the learner
 * wrote (dictation) or said (retell, recognised by Whisper).
 *
 * Matching is forgiving about things the IELTS answer key also accepts or that
 * are formatting only: case, punctuation, digits vs number words ("15" = "fifteen"),
 * "$15" = "15 dollars", and British vs American spelling (centre/center, colour/color).
 */

export type CompareOp =
  | { type: 'match'; expected: string }
  | { type: 'missing'; expected: string }
  | { type: 'wrong'; expected: string; actual: string }
  | { type: 'extra'; actual: string };

export interface CompareResult {
  ops: CompareOp[];
  correct: number;
  total: number;
  /** 0–100, share of original words reproduced correctly. */
  score: number;
}

interface Token {
  display: string;
  key: string;
}

const NUMBER_WORDS: Record<string, string> = {
  zero: '0', oh: '0', nought: '0', one: '1', two: '2', three: '3', four: '4', five: '5', six: '6', seven: '7',
  eight: '8', nine: '9', ten: '10', eleven: '11', twelve: '12', thirteen: '13', fourteen: '14', fifteen: '15',
  sixteen: '16', seventeen: '17', eighteen: '18', nineteen: '19', twenty: '20', thirty: '30', forty: '40',
  fifty: '50', sixty: '60', seventy: '70', eighty: '80', ninety: '90', hundred: '100', first: '1st',
  second: '2nd', third: '3rd'
};

function canonicalSpelling(word: string) {
  return word
    .replace(/our$/, 'or') // colour -> color
    .replace(/ours$/, 'ors')
    .replace(/tre$/, 'ter') // centre -> center
    .replace(/tres$/, 'ters')
    .replace(/is(e|es|ed|ing|ation|ations)$/, 'iz$1') // organise -> organize
    .replace(/ys(e|es|ed|ing)$/, 'yz$1') // analyse -> analyze
    .replace(/lled$/, 'led') // travelled -> traveled
    .replace(/lling$/, 'ling')
    .replace(/ogue$/, 'og'); // catalogue -> catalog
}

function keyOf(piece: string) {
  const word = piece
    .toLowerCase()
    .replace(/[’‘]/g, "'")
    .replace(/^[^a-z0-9]+|[^a-z0-9]+$/g, '')
    .replace(/,(?=\d{3}\b)/g, ''); // 1,000 -> 1000
  if (!word) return '';
  if (NUMBER_WORDS[word]) return NUMBER_WORDS[word];
  if (/^\d+(st|nd|rd|th)$/.test(word)) return word.replace(/(\d+)(st|nd|rd|th)$/, (_m, n: string) => `${n}${ordinalSuffix(n)}`);
  return canonicalSpelling(word);
}

function ordinalSuffix(n: string) {
  const last = n.slice(-1);
  const lastTwo = n.slice(-2);
  if (lastTwo === '11' || lastTwo === '12' || lastTwo === '13') return 'th';
  return last === '1' ? 'st' : last === '2' ? 'nd' : last === '3' ? 'rd' : 'th';
}

export function tokenize(text: string): Token[] {
  const tokens: Token[] = [];
  for (const raw of text.trim().split(/\s+/)) {
    if (!raw) continue;
    // "$15" -> "15 dollars", "20%" -> "20 percent"
    const money = raw.match(/^\$(\d[\d,.]*)(.*)$/);
    const percent = raw.match(/^(\d[\d,.]*)%(.*)$/);
    if (money) {
      tokens.push({ display: raw, key: keyOf(money[1]) });
      tokens.push({ display: '', key: 'dollars' });
      continue;
    }
    if (percent) {
      tokens.push({ display: raw, key: keyOf(percent[1]) });
      tokens.push({ display: '', key: 'percent' });
      continue;
    }
    // Split hyphenated digits/letters ("0475-323-849", "T-H-O-M-P-S-O-N") but keep "well-known".
    const pieces = /^[\w]+(-[\w]+)+[^\w]*$/.test(raw) && raw.split('-').some((p) => p.length <= 1 || /^\d/.test(p))
      ? raw.split('-')
      : [raw];
    for (const piece of pieces) {
      const key = keyOf(piece);
      if (key) tokens.push({ display: piece, key });
    }
  }
  // Display-less helper tokens ("dollars" from "$15") stay attached to the previous token visually.
  return tokens;
}

/** Longest-common-subsequence alignment of original vs attempt. */
export function compareText(original: string, attempt: string): CompareResult {
  const expected = tokenize(original);
  const actual = tokenize(attempt);
  const n = expected.length;
  const m = actual.length;
  const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      lcs[i][j] = expected[i].key === actual[j].key ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }

  const raw: CompareOp[] = [];
  let i = 0;
  let j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && expected[i].key === actual[j].key) {
      raw.push({ type: 'match', expected: expected[i].display });
      i += 1;
      j += 1;
    } else if (j < m && (i === n || lcs[i][j + 1] >= lcs[i + 1][j])) {
      raw.push({ type: 'extra', actual: actual[j].display || actual[j].key });
      j += 1;
    } else {
      raw.push({ type: 'missing', expected: expected[i].display || expected[i].key });
      i += 1;
    }
  }

  // Pair a run of missing words with an adjacent run of extra words as "wrong" (heard X, wrote Y).
  const ops: CompareOp[] = [];
  let k = 0;
  while (k < raw.length) {
    if (raw[k].type === 'match') {
      ops.push(raw[k]);
      k += 1;
      continue;
    }
    const missing: string[] = [];
    const extra: string[] = [];
    while (k < raw.length && raw[k].type !== 'match') {
      const op = raw[k];
      if (op.type === 'missing') missing.push(op.expected);
      if (op.type === 'extra') extra.push(op.actual);
      k += 1;
    }
    const pairs = Math.min(missing.length, extra.length);
    for (let p = 0; p < pairs; p += 1) ops.push({ type: 'wrong', expected: missing[p], actual: extra[p] });
    for (const word of missing.slice(pairs)) ops.push({ type: 'missing', expected: word });
    for (const word of extra.slice(pairs)) ops.push({ type: 'extra', actual: word });
  }

  const correct = ops.filter((op) => op.type === 'match').length;
  const total = n;
  return { ops, correct, total, score: total === 0 ? 0 : Math.round((correct / total) * 100) };
}

/** Clean word for dictionary lookup / pronunciation ("Wednesday," -> "wednesday"). */
export function lookupWord(display: string) {
  return display.toLowerCase().replace(/[’‘]/g, "'").replace(/^[^a-z]+|[^a-z]+$/g, '');
}
