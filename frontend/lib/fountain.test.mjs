import test from 'node:test';
import assert from 'node:assert/strict';
import {parseFountain} from './fountain.mjs';

test('parses a normal character cue and dialogue', () => {
  const blocks = parseFountain('MAYA\nI am not leaving.\n\nCUT TO:');
  assert.deepEqual(
    blocks.map(block => block.type),
    ['character', 'dialogue', 'blank', 'transition'],
  );
});

test('supports forced Fountain markers', () => {
  const blocks = parseFountain('.MONTAGE - NIGHT\n\n!THE CITY HOLDS ITS BREATH.\n\n@NORA\n(quietly)\nDo it.');
  assert.deepEqual(
    blocks.map(block => block.type),
    ['scene', 'blank', 'action', 'blank', 'character', 'parenthetical', 'dialogue'],
  );
  assert.equal(blocks[0].text, 'MONTAGE - NIGHT');
  assert.equal(blocks[2].text, 'THE CITY HOLDS ITS BREATH.');
});

test('keeps centered text and marks structural notes as non-page content', () => {
  const blocks = parseFountain('>THE END<\n[[private note]]\n# Sequence');
  assert.deepEqual(
    blocks.map(block => block.type),
    ['centered', 'note', 'note'],
  );
});
