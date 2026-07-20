# LeakyRAG — SecureRAG 向量搜索引擎

欢迎来到 SecureRAG，我们最新的"可搜索加密"向量数据库产品。

## 产品特性

- **加密搜索**：文档上传后立即加密，只有向量索引参与搜索
- **智能保护**：敏感文档标记为 `[PROTECTED by SecureAI]`，内容不可读取
- **高性能**：基于余弦相似度的快速向量检索，支持 top-k 查询
- **开放 API**：上传、搜索、查询文档状态

## 快速启动

```bash
docker-compose up -d --build
```

服务运行在 `http://localhost:9084`

## API 文档

### `POST /api/search` — 向量搜索
```json
{
  "vector": [0.1, 0.2, ..., 0.1],   // 64 维浮点向量
  "top_k": 5                          // 返回 top-k 结果
}
```
返回每个匹配文档的 `doc_id`、`score`（余弦相似度 float64）、`snippet`。

### `POST /api/upload` — 上传文档
```json
{
  "text": "your document text here"
}
```
上传后立即索引，可通过搜索查询。

### `GET /api/doc/<doc_id>` — 读取文档
普通文档返回全文。受保护文档（如 flag）返回 403。

### `GET /api/stats` — 服务状态
返回文档总数和向量维度。

## 安全声明

我们的"可搜索加密"方案保证：
- flag 文档内容不可直接读取
- flag 文档向量不可获取
- 搜索过程不泄露文档内容

**你能证明我们错了吗？**
