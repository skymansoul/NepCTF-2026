# Vector Blind RAG

炸酱面为其内部知识库部署了一套"隐私保护"的RAG（检索增强生成）系统。为了防止云端向量数据库供应商读取敏感文档内容，他们在上传之前使用非对称标量积保留加密算法（ASPE）对所有文档的嵌入向量进行了加密处理。

他声称：
> *"云端服务商只能看到加密后的向量，相似度检索完全在密文上进行。即使攻击者窃取了整个数据库，没有密钥也无法还原任何明文。"*

### 加密方案

系统在有限域 Z<sub>p</sub> 上运行，其中 p 是一个 256-bit 的大素数。所有向量维数均为 n = 64。

**初始化：** 生成两个随机的秘密可逆矩阵 **M<sub>1</sub>**、**M<sub>2</sub>** ∈ Z<sub>p</sub><sup>n×n</sup>。

**文档向量加密**（离线完成，存入数据库）：

给定文档嵌入向量 **v** ∈ Z<sub>p</sub><sup>n</sup>：

1. 随机拆分 **v**：**v** = **v<sub>1</sub>** + **v<sub>2</sub>** (mod p)
2. 加密：**c<sub>1</sub>** = **v<sub>1</sub>** · **M<sub>1</sub>**<sup>T</sup>， **c<sub>2</sub>** = **v<sub>2</sub>** · **M<sub>2</sub>**<sup>T</sup> (mod p)
3. 存储密文对（**c<sub>1</sub>**，**c<sub>2</sub>**）

**文档加密：** 每份文档使用 AES-256-GCM 加密，密钥由对应向量派生而来：

```
key = SHA256( (v[0] mod 2^256).to_bytes(32, LE) || (v[1] mod 2^256).to_bytes(32, LE) || ... || (v[63] mod 2^256).to_bytes(32, LE) )
```

加密文档的存储格式：`nonce(12字节) || ciphertext || tag(16字节)`，整体以十六进制编码。

**查询预言机**（通过服务器对外暴露）：

给定查询向量 **q** ∈ Z<sub>p</sub><sup>n</sup>：

1. **t<sub>1</sub>** = **q** · **M<sub>1</sub>**<sup>-1</sup>， **t<sub>2</sub>** = **q** · **M<sub>2</sub>**<sup>-1</sup> (mod p)
2. 返回（**t<sub>1</sub>**，**t<sub>2</sub>**）

内积保持性质成立：**c<sub>v</sub>** · **t<sub>q</sub>** = **v** · **q**

## API 接口

### 健康检测

```bash
curl http://<host>:8080/
# {"status": "ok", "service": "Vector Blind RAG Query Oracle", "n": 64}
```

### 下载加密数据库

```bash
curl http://<host>:8080/database
# 返回完整的 challenge_data.json
```

### 查询预言机

```bash
curl -X POST http://<host>:8080/query \
  -H "Content-Type: application/json" \
  -d '{"q": ["1","0","0",...,"0"]}'
# 返回 {"t_q": [[...], [...]]}
```

- `q`：包含 64 个整数的列表（以字符串形式传递）
- `t_q`：包含两个列表，每个列表各有 64 个整数（以字符串返回）
