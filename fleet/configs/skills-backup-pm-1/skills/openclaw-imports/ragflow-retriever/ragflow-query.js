const http = require('http');

const RAGFLOW_CONFIG = {
  baseUrl: process.env.RAGFLOW_BASE_URL || 'http://36.134.158.50:10001',
  agentId: process.env.RAGFLOW_AGENT_ID || '93474e90275e11f1866455338bedff8b',
  apiKey: process.env.RAGFLOW_API_KEY || 'ragflow-hcyEsMcbBXQjQBdqGtBvY9HEoh3toR_-JoSLQMnM5MY'
};

function makeRequest(question) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      question: question,
      stream: false
    });

    const options = {
      hostname: '36.134.158.50',
      port: 10001,
      path: `/api/v1/agents/93474e90275e11f1866455338bedff8b/completions`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ragflow-hcyEsMcbBXQjQBdqGtBvY9HEoh3toR_-JoSLQMnM5MY`,
        'Content-Length': Buffer.byteLength(postData)
      },
      timeout: 600000
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.data && json.data.data && json.data.data.content) {
            resolve(json.data.data.content);
          } else if (json.data && json.data.outputs && json.data.data.outputs.content) {
            resolve(json.data.data.outputs.content);
          } else {
            resolve(JSON.stringify(json));
          }
        } catch (e) {
          reject(new Error('Failed to parse response: ' + e.message));
        }
      });
    });

    req.on('error', (e) => reject(e));
    req.on('timeout', () => req.destroy());

    req.write(postData);
    req.end();
  });
}

if (require.main === module) {
  const question = process.argv.slice(2).join(' ') || 'test';
  console.log('Querying RAGFlow (this takes 5-15 minutes)...');
  makeRequest(question)
    .then(result => console.log(result))
    .catch(err => console.error('Error:', err.message));
}

module.exports = { makeRequest };