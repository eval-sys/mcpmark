## WebArena 外部 Sandbox 启动与评测流程

本文档说明如何复用独立运行的 WebArena Sandbox（`testmfq.py`）来执行 MCPMark 的 `playwright_webarena` 任务。

---

### 1. 启动 WebArena Sandbox

1. **进入 sandbox 脚本目录**
   ```bash
   cd /home/mengfanqing/cua/zhangjin
   ```
2. **推荐使用 tmux/screen 以保持长时间运行**
   ```bash
   tmux new -s webarena_sandbox
   ```
3. **运行 `testmfq.py`**
   ```bash
   python testmfq.py
   ```
   - 程序会创建一个 TTL 5 天的 sandbox，并在 `endpoints_mfq.txt` 中写入所有 endpoint。
   - 日志出现 `Sandbox will keep running for 5 days...` 后，按 `Ctrl+B` 再按 `D` 退出 tmux，保持后台运行。
4. **确认生成文件**
   ```bash
   cat /home/mengfanqing/cua/zhangjin/endpoints_mfq.txt
   ```
   示例：
   ```
   sandbox_id: 1995894166225133574
   homepage: http://10.56.149.80:4399/
   gitlab: http://10.56.149.80:8023/explore
   reddit: http://10.56.149.80:9999/forums/all
   map: http://10.56.149.80:3000/
   wiki: http://10.56.149.80:8888/...
   shopping: http://10.56.149.80:7770/
   shopping_admin: http://10.56.149.80:7780/admin
   ```

---

### 2. 配置 MCPMark 环境变量

在 **`/home/mengfanqing/cua/mcpmark`** 目录下运行：

```bash
cd /home/mengfanqing/cua/mcpmark

# 指向 endpoints 文件
export PLAYWRIGHT_WEBARENA_ENDPOINTS_FILE=/home/mengfanqing/cua/zhangjin/endpoints_mfq.txt

# 如需覆盖单个 URL 可额外设置（可选）
export PLAYWRIGHT_WEBARENA_REDDIT_URL=http://10.56.149.80:9999
export PLAYWRIGHT_WEBARENA_SHOPPING_URL=http://10.56.149.80:7770
export PLAYWRIGHT_WEBARENA_SHOPPING_ADMIN_URL=http://10.56.149.80:7780/admin
export PLAYWRIGHT_WEBARENA_HOMEPAGE_URL=http://10.56.149.80:4399
export PLAYWRIGHT_WEBARENA_GITLAB_URL=http://10.56.149.80:8023/explore
export PLAYWRIGHT_WEBARENA_WIKI_URL=http://10.56.149.80:8888/...
export PLAYWRIGHT_WEBARENA_MAP_URL=http://10.56.149.80:3000

# 模型访问所需的 OpenAI 兼容参数
export OPENAI_BASE_URL=<你的大模型代理地址>
export OPENAI_API_KEY=<你的 API key>
```

> ✅ 只设置 `PLAYWRIGHT_WEBARENA_ENDPOINTS_FILE` 也可以工作，其余覆盖项可按需使用。  
> ✅ 运行 `env | grep PLAYWRIGHT_WEBARENA` 可核对是否生效。

---

### 3. 运行 MCPMark 任务

   ```bash
   python pipeline.py \
     --mcp playwright_webarena \
     --models kimi-k2-thinking \
     --tasks reddit/llm_research_summary \
     --exp-name sandbox-smoke
   ```
   - 日志中应看到 `Using external WebArena endpoints`。
   - `results/<exp>/playwright_webarena__kimi-k2-thinking/run-1/log.txt` 保存完整执行记录。

