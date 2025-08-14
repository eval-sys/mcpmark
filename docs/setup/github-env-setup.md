# GitHub Environment Preparation

This guide walks you through preparing your GitHub environment for MCPLeague and authenticating the CLI tools.

## 📋 **Table of Contents**

<details>
<summary><strong>🔍 Quick Overview - Click to Expand</strong></summary>

### **Phase 1: GitHub Setup**
- [1.1 Create GitHub Organization](#1--prepare-your-evaluation-organization)
- [1.2 Generate Personal Access Token (PAT)](#step-2-generate-fine-grained-personal-access-token-pat)
- [1.3 Configure Environment Variables](#step-3-add-credentials-to-mcp_env)

### **Phase 2: Repository State Setup**
- [2.1 Download Sample Repositories](#2--download-the-sample-repository-state)
- [2.2 Extract and Verify Structure](#quick-setup)

### **Phase 3: Optional Customization**
- [3.1 Add Custom Repositories](#3--add-new-repositories-optional)
- [3.2 Update Configuration Files](#export-process)

### **Phase 4: Understanding Limits**
- [4.1 GitHub Rate Limits](#4--github-rate-limits)
- [4.2 MCPLeague Defaults](#important-limitations)

### **Phase 5: Verification & Troubleshooting**
- [5.1 Quick Checklist](#-quick-checklist)
- [5.2 Common Issues](#-troubleshooting)

**Total Estimated Time**: 15-20 minutes

**Difficulty Level**: ⭐⭐☆☆☆ (Beginner-friendly)

</details>

---

## 🚨 Critical Requirements

> **⚠️ IMPORTANT**: You must enable **ALL permissions** for both Repository and Organization access. Partial permissions can cause authentication failures.

## 1 · Prepare Your Evaluation Organization

### Step 1: Create a GitHub Organization
- **Motivation**: Isolating benchmark repositories from personal codebase.
- **Action**: In GitHub, click your avatar → **Your organizations** → **New organization**
- **Naming**: Naming your new organization (e.g., `mcpleague-eval-xxx`), remember to avoid conflicts.
- **Example** ![Create Org](../../asset/github/github_create_org.png)

### Step 2: Generate Fine-Grained Personal Access Token (PAT)
- **Navigation**: Settings → Developer settings → Personal access tokens → Fine-grained tokens
- **Click**: **Generate new token**
- **Select Owner**: The organization you just created
- **Name**: Use a descriptive name (e.g., *MCPLeague Eval Token*)

#### 🔑 **CRITICAL PERMISSION SETTINGS**
- **Repository permissions**: ✅ **Enable ALL permissions (Read and Write if possible)**
- **Organization permissions**: ✅ **Enable ALL permissions (Read and Write if possible)**
- **Copy the token**: This becomes your `GITHUB_TOKEN`

**Visual Guides**:
- ![Create Token](../../asset/github/github_create_token.png)
- ![Token Permissions](../../asset/github/github_token_permissions.png)

### Step 3: Add Credentials to `.mcp_env`
**File**: Edit (or create) the `.mcp_env` file in your project root
**Add these lines**:
```env
## GitHub
GITHUB_TOKEN="ghp_your-token-here"
GITHUB_EVAL_ORG="mcp-eval"
```

---

## 2 · Download the Sample Repository State

We have pre-exported several popular open-source repositories along with curated Issues and PRs.

### Quick Setup
1. **Download**: Get the archive from [Google Drive](https://drive.google.com/your-link-here)
2. **Extract**: Create the `./github_state/` directory in your project root
3. **Verify**: Ensure the directory structure appears correctly

**Command**:
```bash
mkdir -p github_state
unzip mcpleague_github_state.zip -d ./github_state
```

---

## 3 · Add New Repositories (Optional)

If you want to benchmark additional repositories:

### Export Process
1. **Export repository state**:
   ```bash
   python -m src.mcp_services.github.repo_exporter --repo owner/name --out ./github_state/{your_repo_name}
   ```

2. **Update configuration**:
   - **File**: Open `src/mcp_services/github/state_manager.py`
   - **Action**: Add a new entry to `self.initial_state_mapping` pointing to the exported folder

---

## 4 · GitHub Rate Limits

### ⚠️ **Important Limitations**
- **Fine-grained tokens**: Subject to GitHub write-rate limits
- **Rate limits**: **80 writes per minute** and **500 writes per hour**
- **MCPLeague default**: Caps each repository at **≤ 20 Issues** and **≤ 10 PRs**

---

## 🎯 **Quick Checklist**

Before proceeding, ensure you have:
- [ ] Created GitHub organization (`mcpleague-eval-xxx`)
- [ ] Generated PAT with **ALL permissions enabled**
- [ ] Added `GITHUB_TOKEN` and `GITHUB_EVAL_ORG` to `.mcp_env`
- [ ] Downloaded and extracted `github_state/` directory
- [ ] Verified network connectivity to `api.github.com`

## 🆘 **Troubleshooting**

### Common Issues
- **Authentication failed**: Ensure **ALL permissions** are enabled (not just read)
- **Network timeout**: Check firewall settings or VPN configuration
- **Rate limit exceeded**: Wait for the hourly limit to reset 