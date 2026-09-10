const SCENE_HEADING = /^(INT\.|EXT\.|EST\.|INT\/EXT\.|I\/E\.)/i;
const TRANSITION = /^(FADE (IN|OUT)\.?|CUT TO:|DISSOLVE TO:|SMASH CUT TO:|MATCH CUT TO:|.+ TO:)$/;

function cleanForced(text, marker) {
  return text.startsWith(marker) ? text.slice(marker.length).trim() : text;
}

export function parseFountain(source = '') {
  const lines = String(source).replace(/\r\n?/g, '\n').split('\n');
  const blocks = [];
  let inDialogue = false;
  let previousBlank = true;

  for (let index = 0; index < lines.length; index += 1) {
    const raw = lines[index].replace(/\s+$/, '');
    const text = raw.trim();
    const next = (lines[index + 1] || '').trim();

    if (!text) {
      blocks.push({type: 'blank', text: ''});
      inDialogue = false;
      previousBlank = true;
      continue;
    }

    if (text.startsWith('[[') && text.endsWith(']]')) {
      blocks.push({type: 'note', text: text.slice(2, -2).trim()});
      previousBlank = false;
      continue;
    }

    if (/^#{1,6}\s/.test(text) || text.startsWith('=')) {
      blocks.push({type: 'note', text});
      inDialogue = false;
      previousBlank = false;
      continue;
    }

    if (text.startsWith('>') && text.endsWith('<') && text.length > 2) {
      blocks.push({type: 'centered', text: text.slice(1, -1).trim()});
      inDialogue = false;
      previousBlank = false;
      continue;
    }

    if (text.startsWith('.') || SCENE_HEADING.test(text)) {
      blocks.push({type: 'scene', text: cleanForced(text, '.')});
      inDialogue = false;
      previousBlank = false;
      continue;
    }

    if ((text.startsWith('>') && !text.endsWith('<')) || TRANSITION.test(text)) {
      blocks.push({type: 'transition', text: cleanForced(text, '>')});
      inDialogue = false;
      previousBlank = false;
      continue;
    }

    const forcedCharacter = text.startsWith('@');
    const characterCandidate =
      previousBlank &&
      Boolean(next) &&
      text.length <= 42 &&
      /^[A-Z0-9][A-Z0-9 .'"()#\-]+(?:\^)?$/.test(text);

    if (forcedCharacter || characterCandidate) {
      blocks.push({
        type: 'character',
        text: cleanForced(text, '@').replace(/\^$/, '').trim(),
      });
      inDialogue = true;
      previousBlank = false;
      continue;
    }

    if (inDialogue && /^\(.*\)$/.test(text)) {
      blocks.push({type: 'parenthetical', text});
      previousBlank = false;
      continue;
    }

    if (inDialogue) {
      blocks.push({type: 'dialogue', text: cleanForced(text, '~')});
      previousBlank = false;
      continue;
    }

    blocks.push({type: 'action', text: cleanForced(text, '!')});
    previousBlank = false;
  }

  return blocks;
}
