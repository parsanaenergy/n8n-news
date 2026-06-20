const fs = require('fs');

const workflowStr = fs.readFileSync('workflow.json', 'utf8');
const workflow = JSON.parse(workflowStr);
const node = workflow.nodes.find(n => n.name === 'AI Summarize via DeepSeek');
const code = node.parameters.jsCode;

const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;

let getSummary;
const getSummaryMatch = code.match(/async function getSummary\(itemJson\) \{([\s\S]*?)\n\}/);
const systemPromptMatch = code.match(/const SYSTEM_PROMPT = `([\s\S]*?)`;/);

if (getSummaryMatch && systemPromptMatch) {
  const fnBody = getSummaryMatch[1];
  getSummary = new AsyncFunction('itemJson', `const SYSTEM_PROMPT = \`${systemPromptMatch[1]}\`;\n${fnBody}`);
} else {
  throw new Error("Could not extract getSummary or SYSTEM_PROMPT");
}

describe('AI Summarize via DeepSeek node - getSummary', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  const baseItemJson = {
    company: 'OpenAI',
    title: 'New Model Released',
    jina_content: 'OpenAI released a new super fast model.',
    rss_content: ''
  };

  it('should return a summary on successful API call (happy path)', async () => {
    const mockSummary = 'شرکت OpenAI یک مدل جدید منتشر کرد.';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: [{ message: { content: mockSummary } }]
      })
    });

    const result = await getSummary(baseItemJson);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(result).toBe(mockSummary);
  });

  it('should return an empty string if the fetch response is not ok (e.g. 500 error)', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500
    });

    const result = await getSummary(baseItemJson);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(result).toBe('');
  });

  it('should return an empty string if fetch throws an exception (e.g. network error)', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('Network Error'));

    const result = await getSummary(baseItemJson);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(result).toBe('');
  });

  it('should handle undefined choices or missing content gracefully', async () => {
    // Simulated unexpected response format
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        choices: []
      })
    });

    const result = await getSummary(baseItemJson);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(result).toBe(''); // Based on choices?.[0]?.message?.content || ''
  });
});
