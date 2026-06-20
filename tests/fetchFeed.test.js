const fs = require('fs');
const vm = require('vm');

describe('fetchFeed logic from workflow.json', () => {
  let sandbox;

  beforeEach(() => {
    const workflowStr = fs.readFileSync('workflow.json', 'utf8');
    const workflow = JSON.parse(workflowStr);
    const jsCode = workflow.nodes.find(n => n.name === 'Fetch & Parse RSS Feeds').parameters.jsCode;

    const functionsCode = jsCode.substring(
      jsCode.indexOf('function getTagValue'),
      jsCode.indexOf('const BATCH = 5;')
    );

    const testContextCode = `
      let existingLinks = new Set();

      ${functionsCode}

      this.getTagValue = getTagValue;
      this.cleanHtml = cleanHtml;
      this.fetchFeed = fetchFeed;
      this.setExistingLinks = (links) => { existingLinks = new Set(links); };
    `;

    sandbox = {
      Math: Math,
      RegExp: RegExp,
      String: String,
      Date: Date,
      Set: Set,
      console: console,
      fetch: async () => { throw new Error("fetch not mocked"); }
    };

    vm.createContext(sandbox);
    vm.runInContext(testContextCode, sandbox);
  });

  it('should parse basic RSS items', async () => {
    const mockXml = `
      <rss>
        <channel>
          <title>Test Channel</title>
          <item>
            <title>Item 1</title>
            <link>http://example.com/1</link>
            <description>Desc 1</description>
            <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
          </item>
          <item>
            <title>Item 2</title>
            <link>http://example.com/2</link>
            <description>Desc 2</description>
            <pubDate>Mon, 02 Jan 2024 00:00:00 GMT</pubDate>
          </item>
        </channel>
      </rss>
    `;
    sandbox.fetch = jest.fn().mockResolvedValue({
      ok: true,
      text: jest.fn().mockResolvedValue(mockXml)
    });

    sandbox.setExistingLinks([]);
    const feed = { url: 'http://test.com', company: 'TestCompany' };

    const items = await sandbox.fetchFeed(feed);

    expect(items).toHaveLength(2);
    expect(items[0]).toMatchObject({
      title: 'Item 1',
      link: 'http://example.com/1',
      content: 'Desc 1',
      company: 'TestCompany'
    });
    expect(items[1].title).toBe('Item 2');
  });

  it('should handle Atom feed with link href', async () => {
    const mockXml = `
      <feed>
        <title>Test Atom</title>
        <entry>
          <title>Atom 1</title>
          <link href="http://example.com/atom/1"/>
          <summary>Atom Summary</summary>
          <updated>2024-01-01T00:00:00Z</updated>
        </entry>
      </feed>
    `;
    sandbox.fetch = jest.fn().mockResolvedValue({
      ok: true,
      text: jest.fn().mockResolvedValue(mockXml)
    });

    sandbox.setExistingLinks([]);
    const feed = { url: 'http://test.com', company: 'AtomCompany' };

    const items = await sandbox.fetchFeed(feed);

    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({
      title: 'Atom 1',
      link: 'http://example.com/atom/1',
      content: 'Atom Summary',
      company: 'AtomCompany'
    });
  });

  it('should handle CDATA in tags', async () => {
    const mockXml = `
      <rss>
        <item>
          <title><![CDATA[Title with CDATA]]></title>
          <link>http://example.com/cdata</link>
          <description><![CDATA[<p>Content</p>]]></description>
        </item>
      </rss>
    `;
    sandbox.fetch = jest.fn().mockResolvedValue({
      ok: true,
      text: jest.fn().mockResolvedValue(mockXml)
    });

    sandbox.setExistingLinks([]);
    const feed = { url: 'http://test.com', company: 'Test' };

    const items = await sandbox.fetchFeed(feed);

    expect(items).toHaveLength(1);
    expect(items[0].title).toBe('Title with CDATA');
    expect(items[0].content).toBe('Content'); // cleanHtml strips <p>
  });

  it('should ignore items with missing or short links', async () => {
    const mockXml = `
      <rss>
        <item>
          <title>No Link</title>
        </item>
        <item>
          <title>Short Link</title>
          <link>ab</link>
        </item>
      </rss>
    `;
    sandbox.fetch = jest.fn().mockResolvedValue({
      ok: true,
      text: jest.fn().mockResolvedValue(mockXml)
    });

    sandbox.setExistingLinks([]);
    const feed = { url: 'http://test.com', company: 'Test' };

    const items = await sandbox.fetchFeed(feed);

    expect(items).toHaveLength(0);
  });

  it('should ignore already existing links', async () => {
    const mockXml = `
      <rss>
        <item>
          <title>Existing</title>
          <link>http://example.com/existing</link>
        </item>
        <item>
          <title>New</title>
          <link>http://example.com/new</link>
        </item>
      </rss>
    `;
    sandbox.fetch = jest.fn().mockResolvedValue({
      ok: true,
      text: jest.fn().mockResolvedValue(mockXml)
    });

    sandbox.setExistingLinks(['http://example.com/existing']);
    const feed = { url: 'http://test.com', company: 'Test' };

    const items = await sandbox.fetchFeed(feed);

    expect(items).toHaveLength(1);
    expect(items[0].link).toBe('http://example.com/new');
  });

  it('should cap at 5 items', async () => {
    const mockXml = `<rss>
      ${Array.from({ length: 10 }).map((_, i) => `<item><title>Item ${i}</title><link>http://example.com/${i}</link></item>`).join('')}
    </rss>`;

    sandbox.fetch = jest.fn().mockResolvedValue({
      ok: true,
      text: jest.fn().mockResolvedValue(mockXml)
    });

    sandbox.setExistingLinks([]);
    const feed = { url: 'http://test.com', company: 'Test' };

    const items = await sandbox.fetchFeed(feed);

    expect(items).toHaveLength(5);
  });

  it('should return empty array if fetch fails (res.ok is false)', async () => {
    sandbox.fetch = jest.fn().mockResolvedValue({
      ok: false
    });

    sandbox.setExistingLinks([]);
    const feed = { url: 'http://test.com', company: 'Test' };

    const items = await sandbox.fetchFeed(feed);
    expect(items).toEqual([]);
  });

  it('should return empty array if fetch throws', async () => {
    sandbox.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

    sandbox.setExistingLinks([]);
    const feed = { url: 'http://test.com', company: 'Test' };

    const items = await sandbox.fetchFeed(feed);
    expect(items).toEqual([]);
  });
});
