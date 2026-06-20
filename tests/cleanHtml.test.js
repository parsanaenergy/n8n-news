const fs = require('fs');
const test = require('node:test');
const assert = require('node:assert');

const workflowStr = fs.readFileSync('workflow.json', 'utf8');
const workflow = JSON.parse(workflowStr);

const codeNode = workflow.nodes.find(n => n.name === 'Fetch & Parse RSS Feeds');
const jsCode = codeNode.parameters.jsCode;

const match = jsCode.match(/function cleanHtml\(str\) \{[\s\S]*?\n\}/);
if (!match) {
  throw new Error('cleanHtml function not found in workflow.json');
}

const cleanHtml = new Function('str', match[0] + '\nreturn cleanHtml(str);');

test('cleanHtml tests', async (t) => {
    await t.test('returns empty string for falsy values', () => {
        assert.strictEqual(cleanHtml(null), '');
        assert.strictEqual(cleanHtml(undefined), '');
        assert.strictEqual(cleanHtml(''), '');
    });

    await t.test('removes basic HTML tags', () => {
        assert.strictEqual(cleanHtml('<p>Hello</p>'), 'Hello');
        assert.strictEqual(cleanHtml('<div><b>Bold</b> text</div>'), 'Bold text');
    });

    await t.test('handles multiple HTML entities', () => {
        assert.strictEqual(cleanHtml('Hello&nbsp;World'), 'Hello World');
    });

    await t.test('trims leading and trailing whitespace', () => {
        assert.strictEqual(cleanHtml('  Hello World  '), 'Hello World');
        assert.strictEqual(cleanHtml(' <p>  Hello World  </p> '), 'Hello World');
    });

    await t.test('handles strings with only tags and spaces', () => {
        assert.strictEqual(cleanHtml(' <p> </p> '), '');
    });
});
