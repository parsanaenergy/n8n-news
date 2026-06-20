const fs = require('fs');
const test = require('node:test');
const assert = require('node:assert');
const path = require('path');

test('getTagValue embedded in workflow.json', async (t) => {
  // Read workflow.json
  const workflowPath = path.join(__dirname, '..', 'workflow.json');
  const workflowStr = fs.readFileSync(workflowPath, 'utf8');
  const workflow = JSON.parse(workflowStr);

  // Find the node with the function
  const codeNode = workflow.nodes.find(n => n.name === 'Fetch & Parse RSS Feeds');
  assert.ok(codeNode, 'Found "Fetch & Parse RSS Feeds" node');

  const jsCode = codeNode.parameters.jsCode;

  // Extract getTagValue function definition from the code
  const functionMatch = jsCode.match(/function getTagValue\(xml,\s*tag\)[\s\S]*?\n\}/);
  assert.ok(functionMatch, 'Found getTagValue function definition');

  // Instantiate the function
  const getTagValue = new Function(`
    ${functionMatch[0]}
    return getTagValue;
  `)();

  await t.test('Basic tag parsing', () => {
    assert.strictEqual(getTagValue('<title>Hello World</title>', 'title'), 'Hello World');
  });

  await t.test('Parsing with attributes', () => {
    assert.strictEqual(getTagValue('<title lang="en" class="main">Testing Attributes</title>', 'title'), 'Testing Attributes');
  });

  await t.test('Extracts content from CDATA blocks', () => {
    assert.strictEqual(getTagValue('<description><![CDATA[Some <b>HTML</b> content]]></description>', 'description'), 'Some <b>HTML</b> content');
    // The replace uses /g, so it should handle multiple CDATA blocks correctly within the content
    assert.strictEqual(getTagValue('<content><![CDATA[part1]]> and <![CDATA[part2]]></content>', 'content'), 'part1 and part2');
  });

  await t.test('Returns null for missing tags', () => {
    assert.strictEqual(getTagValue('<title>Not what we want</title>', 'description'), null);
    assert.strictEqual(getTagValue('', 'title'), null);
  });

  await t.test('Handles multiline content', () => {
    const multilineXml = `
      <content>
        Line 1
        Line 2
      </content>
    `;
    assert.strictEqual(getTagValue(multilineXml, 'content'), 'Line 1\n        Line 2');
  });

  await t.test('Case insensitivity for tag names', () => {
    assert.strictEqual(getTagValue('<TiTle>Case Test</tiTle>', 'title'), 'Case Test');
  });

  await t.test('Empty tag', () => {
    assert.strictEqual(getTagValue('<title></title>', 'title'), '');
    assert.strictEqual(getTagValue('<title/>', 'title'), null); // The regex explicitly expects </title>
  });

  await t.test('Whitespace trimming', () => {
    assert.strictEqual(getTagValue('<title>   Spaced Out   </title>', 'title'), 'Spaced Out');
  });
});
