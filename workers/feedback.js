/**
 * Cloudflare Worker - 意見回饋 API
 *
 * 環境變數（secrets）:
 * - GITHUB_TOKEN: GitHub Personal Access Token
 * - IMGBB_API_KEY: imgbb API key
 */

const GITHUB_REPO = 'weiqi-kids/memory-intel';

export default {
  async fetch(request, env) {
    // CORS 預檢
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const { screenshot, message, url } = await request.json();

      if (!message) {
        return jsonResponse({ error: '請輸入意見內容' }, 400);
      }

      // 1. 上傳截圖到 imgbb（如果有的話）
      let imageUrl = null;
      if (screenshot) {
        imageUrl = await uploadToImgbb(screenshot, env.IMGBB_API_KEY);
      }

      // 2. 建立 GitHub issue
      const issueUrl = await createGitHubIssue({
        message,
        imageUrl,
        pageUrl: url,
        token: env.GITHUB_TOKEN,
      });

      return jsonResponse({ success: true, issueUrl });

    } catch (error) {
      console.error('Error:', error);
      return jsonResponse({ error: error.message }, 500);
    }
  },
};

async function uploadToImgbb(base64Data, apiKey) {
  // 移除 data:image/png;base64, 前綴
  const base64 = base64Data.replace(/^data:image\/\w+;base64,/, '');

  const formData = new FormData();
  formData.append('image', base64);

  const response = await fetch(`https://api.imgbb.com/1/upload?key=${apiKey}`, {
    method: 'POST',
    body: formData,
  });

  const result = await response.json();

  if (!result.success) {
    throw new Error('圖片上傳失敗');
  }

  return result.data.url;
}

async function createGitHubIssue({ message, imageUrl, pageUrl, token }) {
  const title = `[意見回饋] ${message.substring(0, 50)}${message.length > 50 ? '...' : ''}`;

  let body = `## 使用者意見\n\n${message}\n\n`;

  if (pageUrl) {
    body += `## 頁面\n\n${pageUrl}\n\n`;
  }

  if (imageUrl) {
    body += `## 截圖\n\n![screenshot](${imageUrl})\n`;
  }

  body += `\n---\n*由意見回饋系統自動建立*`;

  const response = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/issues`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'User-Agent': 'Memory-Intel-Feedback',
    },
    body: JSON.stringify({
      title,
      body,
      labels: ['feedback'],
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`GitHub API 錯誤: ${error}`);
  }

  const issue = await response.json();
  return issue.html_url;
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
