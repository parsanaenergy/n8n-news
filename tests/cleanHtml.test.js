const fs = require('fs');
const path = require('path');
const vm = require('vm');

describe('cleanHtml tests', () => {
  const workflowPath = path.join(__dirname, '..', 'workflow.json');
  const workflowStr = fs.readFileSync(workflowPath, 'utf8');
  const workflow = JSON.parse(workflowStr);
  const codeNode = workflow.nodes.find(n => n.name === 'Fetch & Parse RSS Feeds');
  const jsCode = codeNode.parameters.jsCode;

  const functionMatch = jsCode.match(/function cleanHtml\(str\)[\s\S]*?\n\}/);

  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(functionMatch[0], sandbox);
  const cleanHtml = sandbox.cleanHtml;

  test('returns empty string for falsy values', () => {
    expect(cleanHtml(null)).toBe('');
    expect(cleanHtml(undefined)).toBe('');
    expect(cleanHtml('')).toBe('');
  });

  test('removes basic HTML tags', () => {
    expect(cleanHtml('<div>Hello</div>')).toBe('Hello');
    expect(cleanHtml('<p>This is a <b>test</b>.</p>')).toBe('This is a test.');
    expect(cleanHtml('<br/>Line 1<br>Line 2')).toBe('Line 1Line 2');
  });

  test('handles multiple HTML entities', () => {
    expect(cleanHtml('Jack &amp; Jill')).toBe('Jack   Jill');
    expect(cleanHtml('&lt;b&gt;bold&lt;/b&gt;')).toBe('b  bold  /b'.replace(/  /g, ' '));
    expect(cleanHtml('This&nbsp;is&nbsp;a&nbsp;test')).toBe('This is a test');
  });

  test('trims leading and trailing whitespace', () => {
    expect(cleanHtml('  Hello World  ')).toBe('Hello World');
    expect(cleanHtml('\n\t  Test\n')).toBe('Test');
    expect(cleanHtml(' <p>  Padded  </p> ')).toBe('Padded');
  });

  test('handles strings with only tags and spaces', () => {
    expect(cleanHtml('  <b>  </b>  ')).toBe('');
    expect(cleanHtml('<div> \n </div>')).toBe('');
  });
});
