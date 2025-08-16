# GitHub Environment Preparation

This guide walks you through preparing your GitHub environment for MCPMark and authenticating the CLI tools with support for **token pooling** to mitigate rate limits.

## 📋 **Table of Contents**

<details>
<summary><strong>🔍 Quick Overview - Click to Expand</strong></summary>

### **Phase 1: GitHub Setup**
- [1.1 Create GitHub Organization](#1--prepare-your-evaluation-organization)
- [1.2 Create Multiple GitHub Accounts (Recommended)](#step-2-create-multiple-github-accounts-recommended)
- [1.3 Generate Personal Access Tokens (PATs)](#step-3-generate-fine-grained-personal-access-tokens-pats)
- [1.4 Configure Token Pooling](#step-4-configure-token-pooling-in-mcp_env)

### **Phase 2: Repository State Setup**
- [2.1 Download Sample Repositories](#2--download-the-sample-repository-state)
- [2.2 Extract and Verify Structure](#quick-setup)

### **Phase 3: Optional Customization**
- [3.1 Add Custom Repositories](#3--add-new-repositories-optional)
- [3.2 Update Configuration Files](#export-process)

### **Phase 4: Understanding Limits**
- [4.1 GitHub Rate Limits](#4--mitigating-github-rate-limits-with-token-pooling)
- [4.2 Token Pooling Benefits](#-token-pooling-benefits)

### **Phase 5: Verification & Troubleshooting**
- [5.1 Quick Checklist](#-quick-checklist)
- [5.2 Common Issues](#-troubleshooting)

**Total Estimated Time**: 20-30 minutes
**Difficulty Level**: ⭐⭐⭐☆☆ (Intermediate - requires multiple account setup)

</details>

---

## 🚨 Critical Requirements

> **⚠️ IMPORTANT**: You must enable **ALL permissions** for both Repository and Organization access. Partial permissions can cause authentication failures.

## 1 · Prepare Your Evaluation Organization

<<<<<<< fix/documentation
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
- **Copy and save your PAT token safely**: This serves the `GITHUB_TOKEN`

**Example**
- ![Create Token](../../asset/github/github_create_token.png)
- ![Token Permissions](../../asset/github/github_token_permissions.png)

### Step 3: Create Multiple GitHub Accounts (Recommended for Rate Limit Relief)
To effectively distribute API load and avoid rate limiting, we recommend creating **2-4 additional GitHub accounts**:

#### **Account Setup Process**
- **Create new accounts**: Naming the accounts with something like `your-name-eval-1`, `your-name-eval-2`, etc.
- **Add to organization**: Make all accounts **Owners** of your evaluation organization
- **Generate PATs**: Repeat the token generation process for each account
- **Token naming**: Use descriptive names like *MCPMark Eval Token - Account 1*

#### **Why Multiple Accounts?**
- **Rate limit distribution**: Spread API requests across multiple tokens
- **Automatic failover**: If one account hits limits, others continue working
- **Performance boost**: 4 tokens = 4x capacity for API operations

### Step 4: Configure Token Pooling in `.mcp_env`
**File**: Edit (or create) the `.mcp_env` file in your project root

#### **Multiple Tokens Configuration (Recommended)**
```env
## GitHub - Token Pooling Configuration
GITHUB_TOKENS="token1,token2,token3,token4"
GITHUB_EVAL_ORG="your-eval-org-name"
```

#### **Single Token Configuration (Basic Setup)**
```env
## GitHub - Single Token Configuration
GITHUB_TOKENS="your-single-token-here"
GITHUB_EVAL_ORG="your-eval-org-name"
```

#### **Important Configuration Notes**
- **Token format**: Comma-separated tokens with no spaces
- **Recommended count**: **2-4 tokens** for optimal rate limit distribution
- **Permission consistency**: All tokens must have identical permissions on the evaluation organization
- **Automatic rotation**: The system automatically rotates between tokens to distribute API load
=======
1. **Create a free GitHub Organization**  
   - In GitHub, click your avatar → **Your organizations** → **New organization**.  
   - We recommend a name like `mcpmark-eval-xxx`. (Check if there is a conflict with other organization names.)
   - This keeps all benchmark repositories isolated from your personal and work code.  
   - ![Create Org](../../asset/github/github_create_org.png)

2. **Create Multiple GitHub Accounts (Recommended for Rate Limit Relief)**  
   To effectively distribute API load and avoid rate limiting, we recommend creating **2-4 additional GitHub accounts**:
   - Create new GitHub accounts (e.g., `your-name-eval-1`, `your-name-eval-2`, etc.)
   - **Important**: Add all these accounts as **Owners** to your evaluation organization
   - This allows the token pooling system to distribute requests across multiple accounts

3. **Generate Fine-Grained Personal Access Tokens (PATs) for Each Account**  
   **Repeat this process for each GitHub account (including your main account):**
   - Navigate to *Settings → Developer settings → Personal access tokens → Fine-grained tokens*
   - Click **Generate new token**, select the evaluation organization you created
   - Give the token a descriptive name (e.g., *MCPMark Eval Token - Account 1*)
   - Under **Repository permissions** and **Organization permissions**, enable **All permissions**
   - Copy the generated token — you'll need all tokens for the next step
   - ![Create Token](../../asset/github/github_create_token.png)  
   - ![Token Permissions](../../asset/github/github_token_permissions.png)

4. **Configure Token Pooling in `.mcp_env`**  
   In your project root, edit (or create) the `.mcp_env` file and add your tokens:
   
   **For multiple tokens (Recommended - helps with rate limits):**
   ```env
   ## GitHub - Token Pooling Configuration
   GITHUB_TOKENS="token1,token2,token3,token4"
   GITHUB_EVAL_ORG="your-eval-org-name"
   ```
   
   **For single token (Basic setup):**
   ```env
   ## GitHub - Single Token Configuration
   GITHUB_TOKENS="your-single-token-here"
   GITHUB_EVAL_ORG="your-eval-org-name"
   ```
>>>>>>> main

   **Important Notes:**
   - Replace `token1,token2,token3,token4` with your actual tokens (comma-separated, no spaces)
   - We recommend **2-4 tokens** for optimal rate limit distribution
   - All tokens must have the same permissions on the evaluation organization
   - The system automatically rotates between tokens to distribute API load

---


## 2 · Download the Sample Repository State

We have pre-exported several popular open-source repositories along with curated Issues and PRs.

<<<<<<< fix/documentation
### Quick Setup
1. **Download**: Find the code archive from [Google Drive](https://drive.google.com/your-link-here)
2. **Extract**: Exact the zip file and place the `./github_state/` directory in your project root


**Command**:
```bash
mkdir -p github_state
unzip mcpleague_github_state.zip -d ./github_state
```
=======
1. Download the archive from [Google Drive](https://drive.google.com/drive/folders/16bFDjdtqJYzYJlqKcjKBGomo8DwOhWcN?usp=drive_link).  
2. Extract it so that the directory `./github_state/` appears in the project root:
   ```bash
   mkdir -p github_state
   unzip github_state.zip -d ./github_state
   ```
>>>>>>> main

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

<<<<<<< fix/documentation
## 4 · Mitigating GitHub Rate Limits with Token Pooling

### 📊 **Understanding Rate Limits**

Fine-grained tokens are subject to GitHub API rate limits:

#### **Rate Limit Overview**
- **Read operations**: 5,000 requests per hour per token
- **General write operations**: 80 writes per minute and 500 writes per hour per token
- **Content creation** (Issues, PRs, Comments): 500 requests per hour per token (Secondary Rate Limit)

### 🚀 **Token Pooling Benefits**

MCPMark automatically distributes requests across multiple tokens:

- **Rate limit multiplication**: 4 tokens = 4x capacity
- **Automatic failover**: If one token hits limits, others continue working
- **Load balancing**: Rotates tokens for optimal performance

### 📈 **Capacity Examples**

- **Read operations**: 5,000 → 20,000 requests/hour (with 4 tokens)
- **Content creation**: 500 → 2,000 requests/hour (with 4 tokens)

### 💡 **Key Benefits**

- **Faster evaluations**: Handle large task batches without hitting rate limits
- **Reliable performance**: Automatic failover ensures continuous operation
- **Scalable testing**: Run more frequent evaluations and larger test suites

### ⚠️ **Repository Limits**

**MCPMark caps each repository at ≤ 20 Issues and ≤ 10 PRs by default** to ensure reasonable evaluation times while staying within rate limits.

---

## 🎯 **Quick Checklist**

Before proceeding, ensure you have:
- [ ] Created GitHub organization (`mcpleague-eval-xxx`)
- [ ] Created 2-4 additional GitHub accounts for token pooling
- [ ] Added all accounts as Owners to your evaluation organization
- [ ] Generated PATs with **ALL permissions enabled** for each account
- [ ] Added `GITHUB_TOKENS` and `GITHUB_EVAL_ORG` to `.mcp_env`
- [ ] Downloaded and extracted `github_state/` directory
- [ ] Verified network connectivity to `api.github.com`

## 🆘 **Troubleshooting**

### Common Issues
- **Authentication failed**: Ensure **ALL permissions** are enabled (not just read)
- **Token pooling not working**: Verify all tokens have identical permissions and are comma-separated
- **Rate limit still hit**: Check that you have 2-4 tokens configured for optimal distribution
- **Network timeout**: Check firewall settings or VPN configuration
- **Rate limit exceeded**: Wait for the hourly limit to reset or add more tokens to your pool 
=======
## 4 · GitHub Rate Limits & Token Pooling Benefits

### Understanding Rate Limits
Fine-grained tokens are subject to GitHub API rate limits:
- **Read operations**: 5,000 requests per hour per token
- **General write operations**: 80 writes per minute and 500 writes per hour per token
- **Content creation (Issues, PRs, Comments)**: **500 requests per hour per token** (Secondary Rate Limit)

### How Token Pooling Helps
With **token pooling**, MCPMark automatically:
- **Distributes requests** across multiple tokens to multiply your rate limits
- **Rotates tokens** for each task execution to balance load
- **Handles rate limit failures** by trying the next available token
- **Ensures consistency** between agent execution and verification

### Example: Rate Limit Multiplication
**Read Operations:**
- **Single token**: 5,000 requests/hour
- **4 tokens**: ~20,000 requests/hour total capacity

**Content Creation (Critical for MCPMark):**
- **Single token**: 500 content creation requests/hour
- **4 tokens**: ~2,000 content creation requests/hour total capacity
- **Automatic failover**: If one token hits limits, others continue working

This dramatically improves evaluation performance, especially for large task batches or frequent testing cycles. **The content creation limit is often the bottleneck**, making token pooling essential for efficient evaluations.

### Repository Limits
MCPMark places a cap on the number of PRs and issues (≤ 50 in total) per repository to ensure reasonable evaluation times and to stay within rate limits.