const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

const app = express();
const port = 3000;

// CORS 설정 - 크롬 익스텐션에서 접근 가능하도록
app.use(cors({
  origin: '*', // 모든 출처 허용
  methods: ['GET', 'POST', 'OPTIONS'], // 허용할 HTTP 메서드
  allowedHeaders: ['Content-Type', 'Authorization'] // 허용할 헤더
}));

// 정적 파일 제공 설정
app.use('/static', express.static(path.join(__dirname, 'data')));

// 루트 경로 핸들러
app.get('/', (req, res) => {
  res.send(`
    <h1>Welcome to Data Server</h1>
    <p>Available endpoints:</p>
    <ul>
      <li><a href="/files">/files</a> - Get list of all files</li>
      <li>/data/[filename] - Get content of a specific file</li>
      <li>/static/[filename] - Direct access to files</li>
    </ul>
  `);
});

// /data 경로의 파일 목록을 반환하는 엔드포인트
app.get('/files', (req, res) => {
  const dataDir = path.join(__dirname, 'data');
  fs.readdir(dataDir, (err, files) => {
    if (err) {
      res.status(500).json({ error: 'Failed to read directory' });
      return;
    }
    // 각 파일의 전체 URL을 포함하여 반환
    const fileUrls = files.map(file => ({
      name: file,
      url: `http://localhost:${port}/static/${file}`,
      apiUrl: `http://localhost:${port}/data/${file}`
    }));
    res.json(fileUrls);
  });
});

// /data 폴더의 파일 내용을 제공하는 엔드포인트
app.get('/data/:filename', (req, res) => {
  const filePath = path.join(__dirname, 'data', req.params.filename);
  fs.readFile(filePath, 'utf8', (err, data) => {
    if (err) {
      res.status(404).json({ error: 'File not found' });
      return;
    }
    res.send(data);
  });
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
}); 