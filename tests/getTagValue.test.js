const fs = require('fs');
const assert = require('node:assert');
const path = require('path');
const vm = require('vm');

describe('getTagValue embedded in workflow.json', () => {
  const workflowPath = path.join(__dirname, '..', 'workflow.json');
  const workflowStr = fs.readFileSync(workflowPath, 'utf8');
  const workflow = JSON.parse(workflowStr);

  const codeNode = workflow.nodes.find(n => n.name === 'Fetch & Parse RSS Feeds');
  const jsCode = codeNode.parameters.jsCode;
  const functionMatch = jsCode.match(/function getTagValue\(xml,\s*tag\)[\s\S]*?\n\}/);

  const sandbox = {
    regexCache: {},
    cdataRegex: /<!\[CDATA\[([\s\S]*?)\]\]>/g
  };
  vm.createContext(sandbox);
  vm.runInContext(functionMatch[0], sandbox);
  const getTagValue = sandbox.getTagValue;

  test('Basic tag parsing', () => {
    expect(getTagValue('<title>Hello World</title>', 'title')).toBe('Hello World');
  });

  test('Parsing with attributes', () => {
    expect(getTagValue('<title lang="en" class="main">Testing Attributes</title>', 'title')).toBe('Testing Attributes');
  });

  test('Extracts content from CDATA blocks', () => {
    expect(getTagValue('<description><![CDATA[Some <b>HTML</b> content]]></description>', 'description')).toBe('Some <b>HTML</b> content');
    expect(getTagValue('<content><![CDATA[part1]]> and <![CDATA[part2]]></content>', 'content')).toBe('part1 and part2');
  });

  test('Returns null for missing tags', () => {
    expect(getTagValue('<title>Not what we want</title>', 'description')).toBeNull();
    expect(getTagValue('', 'title')).toBeNull();
  });

  test('Handles multiline content', () => {
    const multilineXml = `
      <content>
        Line 1
        Line 2
      </content>
    `;
    expect(getTagValue(multilineXml, 'content')).toBe('Line 1\n        Line 2');
  });

  test('Case insensitivity for tag names', () => {
    expect(getTagValue('<TiTle>Case Test</tiTle>', 'title')).toBe('Case Test');
  });

  test('Empty tag', () => {
    expect(getTagValue('<title></title>', 'title')).toBe('');
    expect(getTagValue('<title/>', 'title')).toBeNull();
  });

  test('Whitespace trimming', () => {
    expect(getTagValue('<title>   Spaced Out   </title>', 'title')).toBe('Spaced Out');
  });
});
